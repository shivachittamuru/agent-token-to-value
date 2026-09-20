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


def generate_results() -> dict:
    cases = load_dataset(DATASET_PATH)
    usages = []

    with RESULTS_PATH.open("w", encoding="utf-8") as output_file:
        for case in cases:
            print(f"Running agent: {case['name']}")

            response, usage = ask_agent(case["query"])
            usages.append(usage)

            # Foundry validates every uploaded field, so usage stays local.
            result = {
                **case,
                "response": response,
            }

            output_file.write(json.dumps(result) + "\n")

    print(f"Saved agent responses to {RESULTS_PATH}")

    efficiency = summarize_efficiency(usages)
    print_efficiency(efficiency)
    return efficiency


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

    # 1. Run the agent against the regression dataset and measure token usage.
    efficiency = generate_results()

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
