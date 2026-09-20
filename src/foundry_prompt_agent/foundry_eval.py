"""Foundry-side evaluation mechanics: upload, run, poll, and gate.

Everything Foundry-specific lives here so the orchestration script stays thin
and the economics modules stay free of SDK details.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from azure.ai.projects.models import TestingCriterionAzureAIEvaluator
from openai.types.eval_create_params import DataSourceConfigCustom
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    CreateEvalJSONLRunDataSourceParam,
    SourceFileID,
)

DATASET_NAME = "contoso-agent-results"

BEHAVIOR_CRITERION = "contoso_behavior_rubric"
SCOPE_CRITERION = "contoso_scope_adherence"

POLL_SECONDS = 5

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def run_cloud_evaluation(
    project_client,
    *,
    results_path: Path,
    run_id: str,
    judge_model: str,
):
    """Upload results, create the evaluation, run it, and poll to completion."""

    # 1. Upload our generated response dataset to Foundry
    dataset = project_client.datasets.upload_file(
        name=DATASET_NAME,
        version=run_id,
        file_path=str(results_path),
    )

    print(f"Uploaded dataset: {dataset.id}")

    openai_client = project_client.get_openai_client()

    # 2. Tell Foundry what each JSONL row looks like
    data_source_config = DataSourceConfigCustom(
        type="custom",
        item_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "category": {"type": "string"},
                "query": {"type": "string"},
                "ground_truth": {"type": "string"},
                "response": {"type": "string"},
            },
            "required": [
                "query",
                "ground_truth",
                "response",
            ],
        },
    )

    # 3. Define the custom evaluators registered in Foundry.
    # `name` must match the keys read by enforce_quality_gate, and
    # `evaluator_name` must match the names registered in Foundry.
    testing_criteria = [
        TestingCriterionAzureAIEvaluator(
            type="azure_ai_evaluator",
            name=BEHAVIOR_CRITERION,
            evaluator_name=BEHAVIOR_CRITERION,
            initialization_parameters={
                "deployment_name": judge_model,
                "pass_threshold": 0.5,
            },
            data_mapping={
                "query": "{{item.query}}",
                "ground_truth": "{{item.ground_truth}}",
                "response": "{{item.response}}",
            },
        ),
        TestingCriterionAzureAIEvaluator(
            type="azure_ai_evaluator",
            name=SCOPE_CRITERION,
            evaluator_name=SCOPE_CRITERION,
            initialization_parameters={
                "pass_threshold": 0.5,
            },
            data_mapping={
                "category": "{{item.category}}",
                "response": "{{item.response}}",
            },
        ),
    ]

    # 4. Create the evaluation definition in Foundry
    evaluation = openai_client.evals.create(
        name=f"contoso-regression-{run_id}",
        data_source_config=data_source_config,
        testing_criteria=testing_criteria,
    )

    print(f"Created evaluation: {evaluation.id}")

    # 5. Run it against our uploaded JSONL dataset
    run = openai_client.evals.runs.create(
        eval_id=evaluation.id,
        name="contoso-agent-baseline-v2",
        data_source=CreateEvalJSONLRunDataSourceParam(
            type="jsonl",
            source=SourceFileID(
                type="file_id",
                id=dataset.id,
            ),
        ),
    )

    print(f"Started evaluation run: {run.id}")

    # 6. Poll until Foundry finishes
    while run.status not in TERMINAL_STATUSES:
        print(f"Evaluation status: {run.status}")
        time.sleep(POLL_SECONDS)

        run = openai_client.evals.runs.retrieve(
            eval_id=evaluation.id,
            run_id=run.id,
        )

    print(f"Final status: {run.status}")

    if run.status != "completed":
        report_run_failure(openai_client, evaluation.id, run)

    return run


def report_run_failure(openai_client, eval_id: str, run) -> None:
    print(f"\n=== Run did not complete: {run.status} ===")

    run_error = getattr(run, "error", None)
    if run_error:
        print(f"Run-level error: {run_error}")

    counts = getattr(run, "result_counts", None)
    if counts:
        print(f"Result counts: {counts}")

    # Surface per-item errors, which usually explain evaluator failures.
    try:
        output_items = openai_client.evals.runs.output_items.list(
            eval_id=eval_id,
            run_id=run.id,
        )
        for item in output_items:
            for result in getattr(item, "results", []) or []:
                if isinstance(result, dict) and result.get("error"):
                    print(f"- {result.get('name')}: {result['error']}")
    except Exception as exc:  # diagnostics only; never mask the original failure
        print(f"Could not fetch per-item errors: {exc}")


def get_pass_rate(run, evaluator_name: str) -> float:
    for result in run.per_testing_criteria_results or []:
        if result.testing_criteria == evaluator_name:
            total = result.passed + result.failed
            return result.passed / total if total else 0.0

    raise RuntimeError(
        f"Evaluator result not found: {evaluator_name}"
    )


def collect_accepted_work(
    openai_client,
    run,
    *,
    attempted_interactions: int,
    behavior_criterion: str = BEHAVIOR_CRITERION,
    mandatory_guardrails: tuple[str, ...] = (SCOPE_CRITERION,),
) -> dict:
    """Determine Accepted Work per interaction from row-level results.

    A row counts as Accepted Work only when the behavior rubric passes AND
    every mandatory guardrail passes on that same row. Acceptance is decided
    per interaction from Foundry's output items; aggregate pass-rate
    multiplication is intentionally avoided because it is not a valid
    Accepted Work metric.

    The denominator is `attempted_interactions` (the actual workload size),
    not the number of returned rows. If Foundry returns fewer evaluation
    items than were attempted, the missing rows are surfaced and counted
    conservatively as not accepted.
    """

    output_items = openai_client.evals.runs.output_items.list(
        eval_id=run.eval_id,
        run_id=run.id,
    )

    rows = []
    accepted = 0

    for item in output_items:
        passed_by_name = {
            result.name: bool(result.passed)
            for result in getattr(item, "results", []) or []
        }

        behavior_passed = passed_by_name.get(behavior_criterion, False)
        guardrails_passed = all(
            passed_by_name.get(name, False) for name in mandatory_guardrails
        )
        is_accepted = behavior_passed and guardrails_passed

        if is_accepted:
            accepted += 1

        datasource_item = getattr(item, "datasource_item", None) or {}
        rows.append(
            {
                "datasource_item_id": getattr(item, "datasource_item_id", None),
                "name": datasource_item.get("name"),
                "behavior_passed": behavior_passed,
                "guardrails_passed": guardrails_passed,
                "accepted": is_accepted,
            }
        )

    evaluated = len(rows)
    missing = attempted_interactions - evaluated
    # Missing rows have no acceptance evidence, so they count as rejected.
    rejected = attempted_interactions - accepted

    return {
        "attempted_interactions": attempted_interactions,
        "evaluated_interactions": evaluated,
        "missing_interactions": missing,
        "accepted_interactions": accepted,
        "rejected_interactions": rejected,
        "accepted_work_rate": (
            accepted / attempted_interactions if attempted_interactions else 0.0
        ),
        "rows": rows,
    }


def enforce_quality_gate(
    run,
    *,
    behavior_threshold: float,
    scope_threshold: float,
) -> None:
    """Exit non-zero when measured quality regresses below the CI thresholds."""

    if run.status != "completed":
        raise RuntimeError(
            f"Evaluation did not complete successfully: {run.status}"
        )

    behavior_pass_rate = get_pass_rate(run, BEHAVIOR_CRITERION)
    scope_pass_rate = get_pass_rate(run, SCOPE_CRITERION)

    print("\n=== Regression Gate ===")
    print(
        f"Behavior rubric: "
        f"{behavior_pass_rate:.1%} "
        f"(required >= {behavior_threshold:.1%})"
    )
    print(
        f"Scope adherence: "
        f"{scope_pass_rate:.1%} "
        f"(required >= {scope_threshold:.1%})"
    )

    failures = []

    if behavior_pass_rate < behavior_threshold:
        failures.append(
            "Behavior rubric regression: "
            f"{behavior_pass_rate:.1%} "
            f"< {behavior_threshold:.1%}"
        )

    if scope_pass_rate < scope_threshold:
        failures.append(
            "Scope adherence regression: "
            f"{scope_pass_rate:.1%} "
            f"< {scope_threshold:.1%}"
        )

    if failures:
        print("\nQUALITY GATE FAILED")
        for failure in failures:
            print(f"- {failure}")

        sys.exit(1)

    print("\nQUALITY GATE PASSED")
