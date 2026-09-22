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
from foundry_prompt_agent.decision_gates import (
    build_decision_gate_record,
)
from foundry_prompt_agent.economic_value import (
    build_economic_value_record,
)
from foundry_prompt_agent.execution import (
    WORKLOAD_ID,
    apply_acceptance,
    attribute_costs,
    build_execution_records,
    summarize_execution_economics,
)
from foundry_prompt_agent.incremental_economics import (
    build_incremental_economics_record,
)
from foundry_prompt_agent.value_resilience import (
    build_value_resilience_record,
)
from foundry_prompt_agent.workload_assessment import (
    build_workload_assessment,
)
from foundry_prompt_agent.pilot_evidence import (
    build_pilot_evidence_records,
)
from foundry_prompt_agent.portfolio_action import (
    build_portfolio_action_record,
)
from foundry_prompt_agent.run_artifacts import (
    build_interaction_records,
    build_run_summary,
    persist_run_package,
)
from foundry_prompt_agent.synthetic_outcomes import summarize_experiment
from foundry_prompt_agent.synthetic_economics import (
    build_synthetic_economics_record,
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


def run_agent_over_cases(
    cases: list[dict], run_id: str
) -> tuple[dict, list[dict]]:
    usages = []
    entries = []

    with RESULTS_PATH.open("w", encoding="utf-8") as output_file:
        for case in cases:
            print(f"Running agent: {case['name']}")

            response, execution = ask_agent(case["query"])
            usages.append(execution)
            entries.append((case, execution))

            # Upload only the evaluator schema fields; provenance stays local.
            result = {
                "name": case["name"],
                "category": case.get("category"),
                "query": case["query"],
                "ground_truth": case["ground_truth"],
                "response": response,
            }

            output_file.write(json.dumps(result) + "\n")

    print(f"Saved agent responses to {RESULTS_PATH}")

    efficiency = summarize_efficiency(usages)
    print_efficiency(efficiency)

    # Execution Records start with acceptance unknown; joined post-evaluation.
    execution_records = build_execution_records(run_id, entries)
    return efficiency, execution_records


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


def print_synthetic_experiment(summary: dict) -> None:
    print("\n=== Synthetic Business Experiment ===")
    print(f"Eligible interactions: {summary['eligible_interactions']}")
    print(f"Treatment: {summary['treatment_count']}")
    print(f"Control: {summary['control_count']}")
    print(f"Treatment orders: {summary['treatment_orders']}")
    print(f"Control orders: {summary['control_orders']}")
    print(f"Treatment conversion: {summary['treatment_conversion']:.1%}")
    print(f"Control conversion: {summary['control_conversion']:.1%}")
    print(
        f"Simulated conversion lift: "
        f"{summary['simulated_conversion_lift_pp']:.1f} pp"
    )
    print("Evidence: SYNTHETIC SIMULATION")


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


def print_economic_value(record: dict) -> None:
    print("\n=== Economic Value ===")
    print(
        f"Value evidence: "
        f"{record['value_evidence_status'].replace('_', ' ').upper()}"
    )
    print(
        f"Modeled recovered contribution/month: "
        f"${record['modeled_recovered_contribution_usd']:,.2f}"
    )
    print(
        f"Modeled AI Value Multiple: "
        f"{record['modeled_ai_value_multiple']:,.1f}x"
    )

    incremental_orders = record["incremental_orders"]
    print(
        "Incremental orders: "
        + (
            str(incremental_orders)
            if incremental_orders is not None
            else "NOT ESTABLISHED"
        )
    )

    incremental_contribution = record["incremental_contribution_usd"]
    print(
        "Incremental contribution: "
        + (
            f"${incremental_contribution:,.2f}"
            if incremental_contribution is not None
            else "NOT ESTABLISHED"
        )
    )

    print(f"Cost completeness: {record['cost_completeness'].upper()}")

    net_value = record["customer_net_economic_value_usd"]
    print(
        "Customer Net Economic Value: "
        + (
            f"${net_value:,.2f}"
            if net_value is not None
            else "NOT ESTABLISHED"
        )
    )


def print_incremental_economics(record: dict) -> None:
    print("\n=== Incremental Economics ===")

    increment = record["increment_description"]
    print("Proposed increment: " + (increment or "NOT DEFINED"))

    basis = record["economic_basis_id"]
    print("Economic basis: " + (basis or "NOT ESTABLISHED"))

    value = record["incremental_value_usd"]
    print(
        "Incremental value: "
        + (f"${value:,.2f}" if value is not None else "NOT ESTABLISHED")
    )

    cost = record["incremental_customer_cost_usd"]
    print(
        "Incremental customer cost: "
        + (f"${cost:,.2f}" if cost is not None else "NOT ESTABLISHED")
    )

    delta_nev = record["incremental_net_economic_value_usd"]
    print(
        "Incremental Net Economic Value: "
        + (
            f"${delta_nev:,.2f}"
            if delta_nev is not None
            else "NOT ESTABLISHED"
        )
    )


def print_value_resilience(record: dict) -> None:
    print("\n=== Value Resilience ===")
    print(f"Scope: {record['resilience_scope'].replace('_', ' ').upper()}")

    base = record["base_case"]
    print(
        f"Base modeled AI Value Multiple: "
        f"{base['modeled_ai_value_multiple']:,.1f}x"
    )
    print(
        f"Break-even conversion rate: "
        f"{base['break_even_conversion_rate']:.2%}"
    )
    print(f"Stress scenarios evaluated: {len(record['stress_scenarios'])}")
    print(
        f"Resilience classification: "
        f"{record['resilience_status'].replace('_', ' ').upper()}"
    )
    print(f"Structural Unknowns: {len(record['structural_unknowns'])}")
    for unknown in record["structural_unknowns"]:
        print(f"  - {unknown}")


def print_workload_assessment(record: dict) -> None:
    print("\n=== Workload Assessment ===")
    print(
        f"Technical performance: "
        f"{record['technical_performance_status'].replace('_', ' ').upper()}"
    )
    print(f"Execution cost: {record['execution_cost_status'].upper()}")
    print(f"Business outcome: {record['business_outcome_status'].upper()}")
    print(f"Incrementality: {record['incrementality_status'].upper()}")
    print(
        f"Economic value: "
        f"{record['economic_value_status'].replace('_', ' ').upper()}"
    )
    print(
        f"Incremental economics: "
        f"{record['incremental_economics_status'].replace('_', ' ').upper()}"
    )
    print(
        f"Value resilience: "
        f"{record['resilience_scope'].replace('_', ' ').upper()} / "
        f"{record['resilience_status'].replace('_', ' ').upper()}"
    )
    print(f"Decision-critical gaps: {len(record['decision_gaps'])}")
    print(
        f"Assessment: "
        f"{record['assessment_status'].replace('_', ' ').upper()}"
    )


def print_decision_gates(record: dict) -> None:
    gates = record["gates"]

    def status(name: str) -> str:
        return gates[name]["status"].replace("_", " ").upper()

    print("\n=== Decision Gates ===")
    print(f"Decision context: {record['decision_context']}")
    print(f"Strategic / mandatory: {status('strategic_mandatory_gate')}")
    print(f"Value: {status('value_gate')}")
    print(f"Evidence: {status('evidence_gate')}")
    print(f"Value resilience: {status('resilience_gate')}")
    print(f"Incremental economics: {status('incremental_economics_gate')}")
    print(f"Commercial fit: {status('commercial_fit_gate')}")
    print(f"RAI / risk / control: {status('rai_risk_control_gate')}")
    print()
    print(f"Blocking gates: {len(record['blocking_gates'])}")
    print(f"Unknown gates: {len(record['unknown_gates'])}")
    scale_eligible = "YES" if "scale" in record["eligible_actions"] else "NO"
    print(f"Scale eligible: {scale_eligible}")
    print("Final portfolio action: NOT SELECTED")


def print_portfolio_action(record: dict) -> None:
    print("\n=== Portfolio Action ===")
    print(f"Decision context: {record['decision_context']}")
    print(
        f"Primary decision deficit: "
        f"{record['primary_decision_deficit'].replace('_', ' ').upper()}"
    )
    print(f"Selected action: {record['selected_action'].upper()}")
    print(f"Rationale: {record['action_rationale']}")
    print("Authorized next work: bounded evidence-producing pilot")
    owner = record["decision_owner"] or "UNKNOWN"
    print(f"Decision owner: {owner}")
    print(f"Reassessment trigger: {record['reassessment_trigger']}")


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


def process_completed_run(
    *,
    run_id: str,
    cases: list[dict],
    efficiency: dict,
    execution_records: list[dict],
    run,
    run_mode: str = "regression",
    simulation_metadata: dict | None = None,
    pilot_simulator=None,
) -> None:
    """Run the full evidence pipeline for a completed evaluation and persist it.

    Shared by the fixed regression runner and the synthetic workload simulator.
    ``pilot_simulator`` (simulation only) maps acceptance-joined execution
    records to ``(pilot_events, outcome_events)``. Only the tokenomics history
    append is regression-specific.
    """

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

        # 4c. Join acceptance onto Execution Records and summarize.
        execution_records = apply_acceptance(
            execution_records, acceptance["rows"]
        )
        print_execution_evidence(execution_records)

        # 4d. Aggregate defensible execution economics (partial by design).
        attributions = [
            attribute_costs(record) for record in execution_records
        ]
        execution_economics = summarize_execution_economics(
            execution_records, attributions
        )
        print_execution_economics(execution_economics)

        # 4e/4f. Simulated pilot assignment + synthetic outcomes (simulation
        # only). Regression keeps pilot/business evidence Unknown.
        if pilot_simulator is not None:
            pilot_events, outcome_events = pilot_simulator(execution_records)
        else:
            pilot_events, outcome_events = None, None

        # 4e. Business Outcome Evidence.
        business_outcome_records = build_business_outcome_records(
            execution_records, outcome_events=outcome_events
        )
        print_business_outcome_evidence(business_outcome_records)

        # 4f. Pilot Evidence.
        pilot_evidence_records = build_pilot_evidence_records(
            execution_records, pilot_events=pilot_events
        )
        print_pilot_evidence(pilot_evidence_records)

        experiment_summary = None
        if pilot_events is not None:
            experiment_summary = summarize_experiment(pilot_events, outcome_events)
            print_synthetic_experiment(experiment_summary)

        # 5. Load transparent business assumptions.
        assumptions = load_business_assumptions(ASSUMPTIONS_PATH)

        # 5b. Synthetic population economics (simulation only). Kept entirely
        # separate from the production-oriented economic_value contract.
        synthetic_economics_record = None
        synthetic_experiment_section = None
        if experiment_summary is not None:
            synthetic_economics_record = build_synthetic_economics_record(
                experiment_summary=experiment_summary,
                outcome_events=outcome_events,
                contribution_margin=assumptions["contribution_margin"],
                economic_basis_id=f"synthetic-{run_id}",
            )
            synthetic_experiment_section = {
                **experiment_summary,
                "evidence_mode": "synthetic_simulation",
                "counterfactual_method": "randomized_synthetic_control",
            }

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

        # 6b. Economic Value: modeled today; incremental value and Customer
        # Net Economic Value stay Unknown until counterfactual evidence and
        # complete cost exist.
        economic_value_record = build_economic_value_record(
            run_id=run_id,
            workload_id=WORKLOAD_ID,
            modeled_business_economics=business_economics,
            execution_economics=execution_economics,
            incremental_evidence=None,
        )
        print_economic_value(economic_value_record)

        # 6c. Incremental (next-dollar) economics: no proposed increment is
        # defined for this run, so incremental value/cost stay Unknown.
        incremental_economics_record = build_incremental_economics_record(
            workload_id=WORKLOAD_ID,
            decision_id=None,
            increment=None,
        )
        print_incremental_economics(incremental_economics_record)

        # 6d. Value Resilience: modeled scenario sensitivity only. Transparent
        # adverse stress on important modeled drivers; no probabilities.
        conversion_rate = assumptions["conversion_rate"]
        stress_spec = {
            "conversion_rate": [conversion_rate * 0.5, conversion_rate * 0.25],
            "average_order_value_usd": [
                assumptions["average_order_value_usd"] * 0.8
            ],
            "contribution_margin": [
                assumptions["contribution_margin"] * 0.8
            ],
            "cost_stress_multiplier": [5.0, 10.0],
            "combined": [
                {
                    "name": "downturn",
                    "conversion_rate": conversion_rate * 0.5,
                    "cost_stress_multiplier": 5.0,
                }
            ],
        }
        value_resilience_record = build_value_resilience_record(
            workload_id=WORKLOAD_ID,
            measured_run={
                "success_rate": success_rate,
                "cost_per_task": efficiency["cost_per_task"],
            },
            assumptions=assumptions,
            stress_spec=stress_spec,
        )
        print_value_resilience(value_resilience_record)

        # 6e. Workload Assessment: synthesize independent evidence dimensions
        # without recalculating economics or selecting a portfolio action.
        workload_assessment = build_workload_assessment(
            workload_id=WORKLOAD_ID,
            execution_economics=execution_economics,
            economic_value=economic_value_record,
            incremental_economics=incremental_economics_record,
            value_resilience=value_resilience_record,
            business_outcome_records=business_outcome_records,
            pilot_evidence_records=pilot_evidence_records,
            run_mode=run_mode,
            synthetic_experiment=experiment_summary,
        )
        print_workload_assessment(workload_assessment)

        # 7a. Decision Gates: independent DECIDE-phase constraints and action
        # eligibility. No composite score and no final action selection.
        decision_gate_record = build_decision_gate_record(
            workload_id=WORKLOAD_ID,
            decision_id=None,
            decision_context=(
                "Determine what portfolio actions are supportable by the "
                "current evidence."
            ),
            workload_assessment=workload_assessment,
            incremental_economics=incremental_economics_record,
            value_resilience=value_resilience_record,
            commercial_fit=None,
            governance=None,
            strategic_context=None,
        )
        print_decision_gates(decision_gate_record)

        # 7b. Portfolio Action: select the action addressing the primary
        # decision deficit, constrained by gate eligibility.
        portfolio_action_record = build_portfolio_action_record(
            workload_id=WORKLOAD_ID,
            decision_id=None,
            decision_context=(
                "Determine what portfolio action is justified by the "
                "current evidence."
            ),
            workload_assessment=workload_assessment,
            decision_gates=decision_gate_record,
            decision_owner=None,
            decision_date=datetime.now(timezone.utc).isoformat(),
        )
        print_portfolio_action(portfolio_action_record)

        # 7c. Consolidate everything into the run evidence package.
        interaction_records = build_interaction_records(
            run_id=run_id,
            workload_id=WORKLOAD_ID,
            cases=cases,
            execution_records=execution_records,
            business_outcome_records=business_outcome_records,
            pilot_evidence_records=pilot_evidence_records,
            run_mode=run_mode,
        )
        run_summary = build_run_summary(
            run_id=run_id,
            workload_id=WORKLOAD_ID,
            execution_economics=execution_economics,
            modeled_business_economics=business_economics,
            economic_value=economic_value_record,
            incremental_economics=incremental_economics_record,
            value_resilience=value_resilience_record,
            workload_assessment=workload_assessment,
            decision_gates=decision_gate_record,
            portfolio_action=portfolio_action_record,
            run_mode=run_mode,
            evidence_mode=(
                "synthetic_simulation"
                if run_mode == "simulation"
                else "measured_regression"
            ),
            simulation=simulation_metadata,
            synthetic_experiment=synthetic_experiment_section,
            synthetic_economics=synthetic_economics_record,
        )
        interactions_path, summary_path = persist_run_package(
            run_id, interaction_records, run_summary
        )

        print("\n=== Run Evidence Package ===")
        print(f"Mode: {run_mode.upper()}")
        print(f"Run ID: {run_id}")
        print(f"Interactions: {len(interaction_records)}")
        print(f"Saved: {interactions_path}")
        print(f"Saved: {summary_path}")

        # 7. Store the measured + economic results for later comparison. Only
        # the fixed regression suite feeds the tokenomics history / dashboard.
        if run_mode == "regression":
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


def main() -> None:
    judge_model = os.environ["FOUNDRY_JUDGE_MODEL"]

    behavior_threshold = float(
        os.getenv("BEHAVIOR_PASS_RATE_THRESHOLD", "0.90")
    )
    scope_threshold = float(
        os.getenv("SCOPE_PASS_RATE_THRESHOLD", "1.00")
    )

    run_id = build_run_id()

    # 1. Run the agent against the fixed regression dataset and measure it.
    cases = load_dataset(DATASET_PATH)
    efficiency, execution_records = run_agent_over_cases(cases, run_id)

    # 2. Run Foundry evaluation to measure response quality.
    run = run_cloud_evaluation(
        project_client,
        results_path=RESULTS_PATH,
        run_id=run_id,
        judge_model=judge_model,
    )

    print(f"Final status: {run.status}")
    print(f"Foundry report: {run.report_url}")

    # 3. Run the shared evidence pipeline and persist the run package.
    process_completed_run(
        run_id=run_id,
        cases=cases,
        efficiency=efficiency,
        execution_records=execution_records,
        run=run,
        run_mode="regression",
    )

    # 4. CI quality gate remains separate from the economics.
    enforce_quality_gate(
        run,
        behavior_threshold=behavior_threshold,
        scope_threshold=scope_threshold,
    )


if __name__ == "__main__":
    main()
