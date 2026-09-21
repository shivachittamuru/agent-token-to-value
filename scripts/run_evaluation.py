"""Regression evaluation entrypoint.

Run from the repository root:

    uv run scripts/run_evaluation.py

Orchestration only: dataset -> agent -> measured tokens -> Foundry evaluation
-> quality gate -> business economics -> experiment history.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from foundry_prompt_agent import history
from foundry_prompt_agent.agent import ask_agent, project_client
from foundry_prompt_agent.business_economics import (
    load_business_assumptions,
    summarize_business_economics,
)
from foundry_prompt_agent.business_outcomes import (
    build_business_outcome_records,
)
from foundry_prompt_agent.execution import (
    apply_acceptance,
    attribute_costs,
    build_execution_records,
    summarize_execution_economics,
)
from foundry_prompt_agent.pilot_evidence import (
    build_pilot_evidence_records,
)
from foundry_prompt_agent.foundry_eval import (
    BEHAVIOR_CRITERION,
    collect_accepted_work,
    enforce_quality_gate,
    get_pass_rate,
    run_cloud_evaluation,
)
from foundry_prompt_agent.tokenomics import (
    summarize_accepted_work,
    summarize_effectiveness,
    summarize_efficiency,
)

DATASET_PATH = Path("evals/contoso_agent_eval_v3.jsonl")
RESULTS_PATH = Path("evals/results_v3.jsonl")
EXECUTION_RECORDS_PATH = Path("evals/execution_records_v1.jsonl")
BUSINESS_OUTCOME_RECORDS_PATH = Path("evals/business_outcome_records_v1.jsonl")
PILOT_EVIDENCE_RECORDS_PATH = Path("evals/pilot_evidence_records_v1.jsonl")
ASSUMPTIONS_PATH = Path("economics/business_assumptions.yaml")


def build_run_id() -> str:
    github_sha = os.getenv("GITHUB_SHA")

    return (
        github_sha[:8]
        if github_sha
        else datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    )


def load_dataset(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return [
            json.loads(line)
            for line in file
            if line.strip() and not line.lstrip().startswith("//")
        ]


def generate_results(run_id: str) -> tuple[dict, list[dict]]:
    cases = load_dataset(DATASET_PATH)
    usages = []
    entries = []

    with RESULTS_PATH.open("w", encoding="utf-8") as output_file:
        for case in cases:
            print(f"Running agent: {case['name']}")

            response, execution = ask_agent(case["query"])
            usages.append(execution)
            entries.append((case, execution))

            # Foundry validates every uploaded field, so execution stays local.
            result = {
                **case,
                "response": response,
            }

            output_file.write(json.dumps(result) + "\n")

    print(f"Saved agent responses to {RESULTS_PATH}")

    efficiency = summarize_efficiency(usages)
    print_efficiency(efficiency)

    # Execution Records start with acceptance unknown; joined post-evaluation.
    execution_records = build_execution_records(run_id, entries)
    return efficiency, execution_records


def persist_execution_records(records: list[dict]) -> None:
    with EXECUTION_RECORDS_PATH.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record) + "\n")

    print(f"Saved execution records to {EXECUTION_RECORDS_PATH}")


def print_execution_evidence(records: list[dict]) -> None:
    print("\n=== Execution Evidence ===")
    print(f"Interactions: {len(records)}")

    total_cost = sum(record["model_cost_usd"] for record in records)
    print(f"Model cost: ${total_cost:.6f}")

    latencies = [
        record["latency_ms"]
        for record in records
        if record["latency_ms"] is not None
    ]
    average_latency = sum(latencies) / len(latencies) if latencies else 0.0
    print(f"Average latency: {average_latency:,.1f} ms")

    tool_evidence_measured = records and all(
        record["tool_call_count"] is not None for record in records
    )
    print(
        f"Tool-call evidence: "
        f"{'measured' if tool_evidence_measured else 'unavailable'}"
    )


def print_execution_economics(summary: dict) -> None:
    print("\n=== Execution Economics ===")
    print(f"Attempted interactions: {summary['attempted_interactions']}")
    print(f"Accepted work units: {summary['accepted_interactions']}")
    print(
        f"Known direct execution cost: "
        f"${summary['known_direct_execution_cost_usd']:.6f}"
    )
    print(
        f"Known direct cost / attempt: "
        f"${summary['known_direct_cost_per_attempt_usd']:.6f}"
    )
    print(
        f"Known direct cost / accepted work: "
        f"${summary['known_direct_cost_per_accepted_work_usd']:.6f}"
    )
    print(f"Measured tool calls: {summary['measured_tool_calls']}")
    print(f"Cost completeness: {summary['cost_completeness'].upper()}")

    unknown = ", ".join(summary["unknown_or_unallocated_components"]) or "none"
    print(f"Unknown / unallocated: {unknown}")

    if summary["cost_completeness"] == "partial":
        print("Full Execution Cost: NOT YET ESTABLISHED")


def persist_business_outcome_records(records: list[dict]) -> None:
    with BUSINESS_OUTCOME_RECORDS_PATH.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record) + "\n")

    print(f"Saved business outcome records to {BUSINESS_OUTCOME_RECORDS_PATH}")


def print_business_outcome_evidence(records: list[dict]) -> None:
    print("\n=== Business Outcome Evidence ===")
    print(f"Interactions: {len(records)}")

    accepted_units = sum(1 for r in records if r["accepted"] is True)
    print(f"Accepted work units: {accepted_units}")

    with_evidence = sum(
        1 for r in records if r["outcome_evidence_source"] is not None
    )
    print(f"Interactions with downstream outcome evidence: {with_evidence}")

    observed_orders = sum(1 for r in records if r["order_completed"] is True)
    if with_evidence == 0:
        # 0 evidence records is not the same as 0 business outcomes.
        print("Observed completed orders: unknown / 0 observed")
    else:
        print(f"Observed completed orders: {observed_orders} observed")

    has_incrementality = any(
        r["counterfactual_method"] is not None for r in records
    )
    print(
        f"Incrementality evidence: "
        f"{'available' if has_incrementality else 'unavailable'}"
    )


def persist_pilot_evidence_records(records: list[dict]) -> None:
    with PILOT_EVIDENCE_RECORDS_PATH.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record) + "\n")

    print(f"Saved pilot evidence records to {PILOT_EVIDENCE_RECORDS_PATH}")


def print_pilot_evidence(records: list[dict]) -> None:
    print("\n=== Pilot Evidence ===")
    print(f"Interactions: {len(records)}")

    assigned = sum(1 for r in records if r["assignment"] is not None)
    print(f"Pilot-assigned interactions: {assigned}")

    if assigned == 0:
        print("Treatment assignments: unavailable")
        print("Control assignments: unavailable")
        print("Pilot evidence: unavailable")
        return

    treatment = sum(1 for r in records if r["assignment"] == "treatment")
    control = sum(1 for r in records if r["assignment"] == "control")
    print(f"Treatment assignments: {treatment}")
    print(f"Control assignments: {control}")
    print("Pilot evidence: available")


def print_efficiency(summary: dict) -> None:
    print("\n=== Token Efficiency ===")
    print(f"Tasks: {summary['tasks']}")
    print(f"Total tokens: {summary['total_tokens']:,}")
    print(f"Tokens per task: {summary['tokens_per_task']:,.1f}")
    print(f"  input/task:  {summary['input_tokens_per_task']:,.1f}")
    print(f"  output/task: {summary['output_tokens_per_task']:,.1f}")
    print(f"Total cost: ${summary['total_cost']:.6f}")
    print(f"Cost per task: ${summary['cost_per_task']:.6f}")


def print_effectiveness(summary: dict) -> None:
    print("\n=== Token Effectiveness ===")
    print(f"Success rate: {summary['success_rate']:.1%}")
    print(f"Successful tasks: {summary['successful_tasks']:.1f}")
    print(f"Tokens per success: {summary['tokens_per_success']:,.1f}")
    print(f"Cost per success: ${summary['cost_per_success']:.6f}")


def print_accepted_work(acceptance: dict, economics: dict) -> None:
    print("\n=== Accepted Work ===")
    print(f"Attempted interactions: {acceptance['attempted_interactions']}")
    print(f"Evaluated interactions: {acceptance['evaluated_interactions']}")
    print(f"Accepted interactions: {acceptance['accepted_interactions']}")
    print(f"Rejected interactions: {acceptance['rejected_interactions']}")
    print(f"Accepted work rate: {acceptance['accepted_work_rate']:.1%}")
    print(
        f"Tokens per accepted work: "
        f"{economics['tokens_per_accepted_work']:,.1f}"
    )
    print(
        f"Cost per accepted work: "
        f"${economics['cost_per_accepted_work']:.6f}"
    )

    missing = acceptance["missing_interactions"]
    if missing > 0:
        print(
            f"WARNING: {missing} attempted interaction(s) returned no "
            f"row-level evaluation evidence; counted as rejected."
        )

    rejected_rows = [row for row in acceptance["rows"] if not row["accepted"]]
    if rejected_rows:
        print("Rejected interactions:")
        for row in rejected_rows:
            behavior = "pass" if row["behavior_passed"] else "fail"
            guardrails = "pass" if row["guardrails_passed"] else "fail"
            print(
                f"  - {row['name']}: "
                f"behavior={behavior} guardrails={guardrails}"
            )


def print_business_economics(summary: dict) -> None:
    print("\n=== Business Economics ===")

    print(
        f"Addressable contacts/day: "
        f"{summary['addressable_contacts_per_day']:.1f}"
    )

    print(
        f"Successful contacts/day: "
        f"{summary['successful_contacts_per_day']:.1f}"
    )

    print(
        f"Recovered orders/day: "
        f"{summary['recovered_orders_per_day']:.1f}"
    )

    print(
        f"Recovered revenue/month: "
        f"${summary['recovered_revenue_per_month']:,.2f}"
    )

    print(
        f"Recovered contribution/month: "
        f"${summary['recovered_contribution_per_month']:,.2f}"
    )

    print(
        f"AI inference cost/month: "
        f"${summary['ai_inference_cost_per_month']:,.2f}"
    )

    print(
        f"AI Value Multiple: "
        f"{summary['ai_value_multiple']:,.1f}x"
    )

    print(
        f"Break-even conversion rate: "
        f"{summary['break_even_conversion_rate']:.2%}"
    )


def build_history_record(
    run_id: str,
    efficiency: dict,
    effectiveness: dict,
    assumptions: dict,
    business_economics: dict,
) -> dict:
    return {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),

        # Measured token efficiency
        "tasks": efficiency["tasks"],
        "total_tokens": efficiency["total_tokens"],
        "total_cost": efficiency["total_cost"],
        "tokens_per_task": efficiency["tokens_per_task"],
        "cost_per_task": efficiency["cost_per_task"],

        # Measured effectiveness
        "success_rate": effectiveness["success_rate"],
        "successful_tasks": effectiveness["successful_tasks"],
        "cost_per_success": effectiveness["cost_per_success"],

        # Business assumptions used for this run
        "missed_contacts_per_day": assumptions["missed_contacts_per_day"],
        "ai_eligible_rate": assumptions["ai_eligible_rate"],
        "conversion_rate": assumptions["conversion_rate"],
        "average_order_value_usd": assumptions["average_order_value_usd"],
        "contribution_margin": assumptions["contribution_margin"],
        "days_per_month": assumptions["days_per_month"],

        # Modeled business economics
        **business_economics,
    }


def main() -> None:
    judge_model = os.environ["FOUNDRY_JUDGE_MODEL"]

    behavior_threshold = float(
        os.getenv("BEHAVIOR_PASS_RATE_THRESHOLD", "0.90")
    )
    scope_threshold = float(
        os.getenv("SCOPE_PASS_RATE_THRESHOLD", "1.00")
    )

    run_id = build_run_id()

    # 1. Run the agent against the regression dataset and measure execution.
    efficiency, execution_records = generate_results(run_id)

    # 2. Run Foundry evaluation to measure response quality.
    run = run_cloud_evaluation(
        project_client,
        results_path=RESULTS_PATH,
        run_id=run_id,
        judge_model=judge_model,
    )

    print(f"Final status: {run.status}")
    print(f"Foundry report: {run.report_url}")

    if run.status == "completed":
        # 3. Measured quality signal.
        success_rate = get_pass_rate(run, BEHAVIOR_CRITERION)

        # 4. Quality-adjusted token efficiency.
        effectiveness = summarize_effectiveness(efficiency, success_rate)
        print_effectiveness(effectiveness)

        # 4b. Accepted Work: per-interaction acceptance from row-level results.
        openai_client = project_client.get_openai_client()
        acceptance = collect_accepted_work(
            openai_client, run, attempted_interactions=efficiency["tasks"]
        )
        accepted_work = summarize_accepted_work(
            efficiency,
            accepted_interactions=acceptance["accepted_interactions"],
            attempted_interactions=acceptance["attempted_interactions"],
        )
        print_accepted_work(acceptance, accepted_work)

        # 4c. Join acceptance onto Execution Records, persist, and summarize.
        execution_records = apply_acceptance(
            execution_records, acceptance["rows"]
        )
        persist_execution_records(execution_records)
        print_execution_evidence(execution_records)

        # 4d. Aggregate defensible execution economics (partial by design).
        attributions = [
            attribute_costs(record) for record in execution_records
        ]
        execution_economics = summarize_execution_economics(
            execution_records, attributions
        )
        print_execution_economics(execution_economics)

        # 4e. Business Outcome Evidence: no downstream system yet, so all
        # downstream fields correctly persist as Unknown (None).
        business_outcome_records = build_business_outcome_records(
            execution_records, outcome_events=None
        )
        persist_business_outcome_records(business_outcome_records)
        print_business_outcome_evidence(business_outcome_records)

        # 4f. Pilot Evidence: no pilot is running, so pilot metadata stays
        # Unknown (None). Nothing is assigned, simulated, or randomized.
        pilot_evidence_records = build_pilot_evidence_records(
            execution_records, pilot_events=None
        )
        persist_pilot_evidence_records(pilot_evidence_records)
        print_pilot_evidence(pilot_evidence_records)

        # 5. Load transparent business assumptions.
        assumptions = load_business_assumptions(ASSUMPTIONS_PATH)

        # 6. Combine measured AI performance with business assumptions.
        business_economics = summarize_business_economics(
            missed_contacts_per_day=assumptions["missed_contacts_per_day"],
            ai_eligible_rate=assumptions["ai_eligible_rate"],
            success_rate=success_rate,
            conversion_rate=assumptions["conversion_rate"],
            average_order_value_usd=assumptions["average_order_value_usd"],
            contribution_margin=assumptions["contribution_margin"],
            cost_per_task_usd=efficiency["cost_per_task"],
            days_per_month=assumptions["days_per_month"],
        )

        print_business_economics(business_economics)

        # 7. Store the measured + economic results for later comparison.
        history.append_run(
            build_history_record(
                run_id,
                efficiency,
                effectiveness,
                assumptions,
                business_economics,
            )
        )

        print(f"\nAppended tokenomics run to {history.HISTORY_PATH}")

    # 8. CI quality gate remains separate from the economics.
    enforce_quality_gate(
        run,
        behavior_threshold=behavior_threshold,
        scope_threshold=scope_threshold,
    )


if __name__ == "__main__":
    main()
