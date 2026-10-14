"""Pure presentation helpers for the Value-to-Action dashboard.

These functions map stored run-package fields into display-ready structures.
The scenario helper delegates runtime-economics arithmetic to the established
pure helper. No function calls the agent/Azure/Foundry or invents values:
missing optional fields remain unavailable, and Unknown statuses do not get a
fabricated scope.
"""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite

from foundry_prompt_agent.azure_runtime_cost import (
    apply_azure_runtime_cost_to_modeled_economics,
)

UNAVAILABLE = "—"

JOURNEY_STAGES = ("MEASURE", "PROVE", "VALUE", "TEST", "DECIDE", "ACT")
VALUE_PULSE_OBJECTIVE = (
    "Recover customer demand the business cannot currently serve."
)
VALUE_PULSE_ACCEPTED_WORK = (
    "Task success plus mandatory quality and control floors."
)


def _upper(value) -> str:
    if value is None:
        return "UNKNOWN"
    return str(value).replace("_", " ").upper()


def run_metadata(summary: dict, interactions: list[dict]) -> dict:
    simulation = summary.get("simulation") or {}
    return {
        "run_id": summary.get("run_id"),
        "run_mode": summary.get("run_mode", "regression"),
        "evidence_mode": summary.get("evidence_mode"),
        "interaction_count": len(interactions),
        "inquiry_seed": simulation.get("inquiry_seed"),
        "outcome_seed": simulation.get("outcome_seed"),
        "generator_version": simulation.get("generator_version"),
        "outcome_simulator_version": simulation.get("outcome_simulator_version"),
    }


def is_simulation(summary: dict) -> bool:
    return summary.get("run_mode") == "simulation"


def journey_states(summary: dict) -> dict:
    """Map stored fields to a concise six-stage state (presentation only)."""

    assessment = summary.get("workload_assessment") or {}
    gates = (summary.get("decision_gates") or {}).get("gates") or {}
    action = summary.get("portfolio_action") or {}

    technical = assessment.get("technical_performance_status")
    measure = "ESTABLISHED" if technical == "established" else _upper(technical)

    if summary.get("synthetic_experiment"):
        prove = "SIMULATED"
    elif assessment.get("business_outcome_status") == "observed":
        prove = "OBSERVED"
    else:
        prove = "UNKNOWN"

    if summary.get("synthetic_economics"):
        value = "SIMULATED / MODELED"
    elif assessment.get("economic_value_status") == "modeled_only":
        value = "MODELED"
    else:
        value = _upper(assessment.get("economic_value_status"))

    test = _upper(assessment.get("execution_cost_status"))

    gate_statuses = {g.get("status") for g in gates.values()}
    if "fail" in gate_statuses:
        decide = "BLOCKED"
    elif "conditional" in gate_statuses:
        decide = "CONDITIONAL"
    elif gate_statuses:
        decide = "OPEN"
    else:
        decide = UNAVAILABLE

    act = _upper(action.get("selected_action"))

    return {
        "MEASURE": measure,
        "PROVE": prove,
        "VALUE": value,
        "TEST": test,
        "DECIDE": decide,
        "ACT": act,
    }


def measure_metrics(summary: dict, interactions: list[dict]) -> dict:
    economics = summary.get("execution_economics") or {}
    attempted = economics.get("attempted_interactions", len(interactions))
    accepted = economics.get("accepted_interactions")
    if accepted is None:
        accepted = sum(
            1
            for record in interactions
            if (record.get("acceptance") or {}).get("accepted") is True
        )

    acceptance_rate = accepted / attempted if attempted else 0.0

    return {
        "attempted_interactions": attempted,
        "accepted_interactions": accepted,
        "acceptance_rate": acceptance_rate,
        "known_direct_execution_cost_usd": economics.get(
            "known_direct_execution_cost_usd"
        ),
        "known_direct_cost_per_accepted_work_usd": economics.get(
            "known_direct_cost_per_accepted_work_usd"
        ),
        "measured_tool_calls": economics.get("measured_tool_calls"),
        "cost_completeness": economics.get("cost_completeness"),
    }


def prove_view(summary: dict) -> dict | None:
    """Return the synthetic experiment view, or None when unavailable."""

    experiment = summary.get("synthetic_experiment")
    if not experiment:
        return None
    return dict(experiment)


def value_view(summary: dict) -> dict:
    """Map stored economics to separate model, system, and customer layers."""

    modeled_economics = summary.get("modeled_business_economics") or {}
    economic_value = summary.get("economic_value") or {}
    synthetic = summary.get("synthetic_economics")
    runtime_cost = summary.get("azure_runtime_cost")
    runtime_modeled = summary.get("azure_runtime_modeled_economics")

    incremental = summary.get("incremental_economics") or {}
    incremental_established = (
        incremental.get("economics_status")
        == "incremental_net_value_established"
    )

    azure_runtime = None
    if runtime_cost is not None or runtime_modeled is not None:
        runtime_cost = runtime_cost or {}
        runtime_modeled = runtime_modeled or {}
        azure_runtime = {
            "available": bool(runtime_cost and runtime_modeled),
            "actual_selected_resource_cost_usd": runtime_cost.get(
                "actual_selected_resource_cost_usd"
            ),
            "allocated_azure_runtime_cost_usd": runtime_cost.get(
                "allocated_azure_runtime_cost_usd",
                runtime_modeled.get("allocated_azure_runtime_cost_usd"),
            ),
            "modeled_contribution_after_azure_runtime_usd": runtime_modeled.get(
                "modeled_contribution_after_azure_runtime_usd"
            ),
            "modeled_azure_runtime_value_multiple": runtime_modeled.get(
                "modeled_azure_runtime_value_multiple"
            ),
            "allocation_status": runtime_cost.get(
                "allocation_status", runtime_modeled.get("allocation_status")
            ),
            "cost_period": runtime_cost.get(
                "cost_period", runtime_modeled.get("cost_period")
            ),
        }

    return {
        "modeled": {
            "recovered_contribution_usd": modeled_economics.get(
                "recovered_contribution_per_month"
            ),
            "inference_cost_usd": modeled_economics.get(
                "ai_inference_cost_per_month"
            ),
            "ai_value_multiple": modeled_economics.get("ai_value_multiple"),
            "cost_completeness": economic_value.get("cost_completeness"),
        },
        "azure_runtime": azure_runtime,
        "synthetic": dict(synthetic) if synthetic else None,
        "decision_grade": {
            "customer_net_economic_value_usd": economic_value.get(
                "customer_net_economic_value_usd"
            ),
            # Only surface production incremental NEV when actually established.
            "incremental_net_economic_value_usd": (
                incremental.get("incremental_net_economic_value_usd")
                if incremental_established
                else None
            ),
        },
    }


def scenario_runtime_economics(
    *,
    modeled_business_economics: dict,
    cost_snapshot: dict,
    workload_id: str,
    modeled_days_per_month: int,
) -> dict | None:
    """Calculate a scenario's system lens against a fixed validated month.

    Returns None when workload or modeled period does not match the snapshot.
    All arithmetic is delegated to the established runtime economics helper.
    """
    if cost_snapshot.get("workload_id") != workload_id:
        return None
    if cost_snapshot.get("period_days") != modeled_days_per_month:
        return None
    return apply_azure_runtime_cost_to_modeled_economics(
        modeled_business_economics=modeled_business_economics,
        azure_runtime_cost={
            "allocated_azure_runtime_cost_usd": cost_snapshot[
                "allocated_azure_runtime_cost_usd"
            ],
            "cost_period": cost_snapshot["cost_period"],
            "cost_source": cost_snapshot["evidence_source"],
            "allocation_status": cost_snapshot["allocation_status"],
        },
    )


def _status_scope_row(dimension: str, status, scope) -> dict:
    status_text = _upper(status)
    # Do not attach a scope to an Unknown status.
    if status_text == "UNKNOWN" or scope in (None, "regression", "none"):
        scope_text = UNAVAILABLE
    else:
        scope_text = _upper(scope)
    return {"dimension": dimension, "status": status_text, "scope": scope_text}


def test_evidence_rows(summary: dict) -> list[dict]:
    assessment = summary.get("workload_assessment") or {}
    resilience = summary.get("value_resilience") or {}

    return [
        _status_scope_row(
            "Technical performance",
            assessment.get("technical_performance_status"),
            assessment.get("technical_evidence_scope"),
        ),
        _status_scope_row(
            "Business outcome",
            assessment.get("business_outcome_status"),
            assessment.get("business_evidence_scope"),
        ),
        _status_scope_row(
            "Incrementality",
            assessment.get("incrementality_status"),
            assessment.get("incrementality_evidence_scope"),
        ),
        _status_scope_row(
            "Execution cost", assessment.get("execution_cost_status"), None
        ),
        _status_scope_row(
            "Economic value", assessment.get("economic_value_status"), None
        ),
        _status_scope_row(
            "Incremental economics",
            assessment.get("incremental_economics_status"),
            None,
        ),
        _status_scope_row(
            "Value resilience",
            resilience.get("resilience_status"),
            resilience.get("resilience_scope"),
        ),
    ]


def assessment_claims(summary: dict) -> dict:
    assessment = summary.get("workload_assessment") or {}
    return {
        "established": assessment.get("established_claims") or [],
        "simulated": assessment.get("simulated_claims") or [],
        "modeled": assessment.get("modeled_claims") or [],
        "unknown": assessment.get("unknown_claims") or [],
    }


def decide_gate_rows(summary: dict) -> list[dict]:
    gates = (summary.get("decision_gates") or {}).get("gates") or {}
    order = (
        "strategic_mandatory_gate",
        "value_gate",
        "evidence_gate",
        "resilience_gate",
        "incremental_economics_gate",
        "commercial_fit_gate",
        "rai_risk_control_gate",
    )
    labels = {
        "strategic_mandatory_gate": "Strategic / mandatory",
        "value_gate": "Value",
        "evidence_gate": "Evidence",
        "resilience_gate": "Value resilience",
        "incremental_economics_gate": "Incremental economics",
        "commercial_fit_gate": "Commercial fit",
        "rai_risk_control_gate": "RAI / risk / control",
    }
    rows = []
    for key in order:
        gate = gates.get(key)
        if not gate:
            continue
        rows.append(
            {
                "gate": labels[key],
                "status": _upper(gate.get("status")),
                "rationale": gate.get("rationale", ""),
            }
        )
    return rows


def decide_actions(summary: dict) -> dict:
    gates = summary.get("decision_gates") or {}
    ineligible = gates.get("ineligible_actions") or []
    return {
        "eligible": gates.get("eligible_actions") or [],
        "ineligible": [
            entry.get("action") if isinstance(entry, dict) else entry
            for entry in ineligible
        ],
        "scale_eligible": "scale" in (gates.get("eligible_actions") or []),
    }


def act_view(summary: dict) -> dict:
    action = summary.get("portfolio_action") or {}
    return {
        "selected_action": _upper(action.get("selected_action")),
        "primary_decision_deficit": _upper(
            action.get("primary_decision_deficit")
        ),
        "action_rationale": action.get("action_rationale"),
        "required_work": action.get("required_work") or [],
        "required_evidence": action.get("required_evidence") or [],
        "resource_request": action.get("resource_request"),
        "reassessment_trigger": action.get("reassessment_trigger"),
    }


def build_value_pulse_view(summary: dict, interactions: list[dict]) -> dict:
    """Compose existing run evidence into the compact Value Pulse stages."""

    workload_id = summary.get("workload_id")
    workload_name = summary.get("workload_name") or (
        str(workload_id).replace("-", " ").title()
        if workload_id
        else UNAVAILABLE
    )
    runtime_cost_record = summary.get("azure_runtime_cost") or {}
    runtime_workload_matches = (
        bool(runtime_cost_record)
        and runtime_cost_record.get("workload_id") == workload_id
    )
    runtime_cost = (
        runtime_cost_record if runtime_workload_matches else {}
    )
    cost_period = runtime_cost.get("cost_period")
    period_label = UNAVAILABLE
    if cost_period:
        try:
            period_start = date.fromisoformat(cost_period["start"])
            period_label = period_start.strftime("%b %Y")
        except (KeyError, TypeError, ValueError):
            period_label = UNAVAILABLE
    elif summary.get("run_id"):
        try:
            run_date = datetime.strptime(
                str(summary["run_id"])[:8], "%Y%m%d"
            ).date()
            period_label = run_date.strftime("%b %d, %Y")
        except (TypeError, ValueError):
            period_label = str(summary["run_id"])

    measure = measure_metrics(summary, interactions)
    attempted = measure["attempted_interactions"]
    accepted_count = (
        measure["accepted_interactions"] if attempted else None
    )
    accepted_rate = measure["acceptance_rate"] if attempted else None
    direct_cost_per_accepted_work = measure[
        "known_direct_cost_per_accepted_work_usd"
    ]
    if (
        accepted_count is None
        or accepted_count <= 0
        or isinstance(direct_cost_per_accepted_work, bool)
        or not isinstance(direct_cost_per_accepted_work, (int, float))
        or not isfinite(direct_cost_per_accepted_work)
    ):
        direct_cost_per_accepted_work = None

    value = value_view(summary)
    runtime_value = value["azure_runtime"]
    runtime_economics_available = bool(
        runtime_workload_matches
        and runtime_value
        and runtime_value["available"]
    )
    if runtime_economics_available:
        economic_value_label = "Modeled contribution after Azure runtime"
        economic_value_amount = runtime_value[
            "modeled_contribution_after_azure_runtime_usd"
        ]
        value_multiple_label = "Modeled Azure Runtime Value Multiple"
        value_multiple = runtime_value["modeled_azure_runtime_value_multiple"]
        value_evidence_type = "MODELED"
    else:
        economic_value_label = "Modeled recovered contribution"
        economic_value_amount = value["modeled"]["recovered_contribution_usd"]
        value_multiple_label = "Modeled AI Value Multiple (inference-only)"
        value_multiple = value["modeled"]["ai_value_multiple"]
        value_evidence_type = (
            "MODELED" if economic_value_amount is not None else "UNKNOWN"
        )

    assessment = summary.get("workload_assessment") or {}
    evidence_scope = str(assessment.get("business_evidence_scope") or "").lower()
    observed_outcomes = []
    simulated_outcomes = []
    for record in interactions:
        outcome = record.get("business_outcome") or {}
        source = outcome.get("outcome_evidence_source")
        has_outcome = source is not None or any(
            outcome.get(field) is not None
            for field in (
                "customer_engaged_after_response",
                "order_completed",
                "order_value_usd",
                "incremental_order",
            )
        )
        if not has_outcome:
            continue
        if source == "synthetic_simulation" or record.get("run_mode") == "simulation":
            simulated_outcomes.append(outcome)
        else:
            observed_outcomes.append(outcome)

    experiment = summary.get("synthetic_experiment") or {}
    synthetic_economics = summary.get("synthetic_economics") or {}
    if (
        summary.get("run_mode") == "simulation"
        or evidence_scope == "simulation"
        or experiment
        or simulated_outcomes
    ):
        outcome = {
            "evidence_type": "SIMULATED",
            "primary_metric_label": "Synthetic conversion lift",
            "primary_metric_value": experiment.get(
                "simulated_conversion_lift_pp"
            ),
            "primary_metric_unit": "percentage points",
            "magnitude_label": "Simulated incremental orders (sample)",
            "magnitude_value": synthetic_economics.get(
                "simulated_incremental_orders_for_observed_sample"
            ),
            "magnitude_unit": "orders",
            "production_status": "Not established",
        }
    elif observed_outcomes or (
        assessment.get("business_outcome_status") == "observed"
        and evidence_scope != "simulation"
    ):
        observed_orders = [
            item
            for item in observed_outcomes
            if item.get("order_completed") is not None
        ]
        observed_order_values = [
            item["order_value_usd"]
            for item in observed_outcomes
            if isinstance(item.get("order_value_usd"), (int, float))
            and not isinstance(item.get("order_value_usd"), bool)
        ]
        if observed_orders:
            outcome_metric_label = "Observed completed orders"
            outcome_metric_value = sum(
                item["order_completed"] is True for item in observed_orders
            )
            outcome_metric_unit = "orders"
        else:
            outcome_metric_label = "Observed business outcome evidence"
            outcome_metric_value = None
            outcome_metric_unit = None
        outcome = {
            "evidence_type": "OBSERVED",
            "primary_metric_label": outcome_metric_label,
            "primary_metric_value": outcome_metric_value,
            "primary_metric_unit": outcome_metric_unit,
            "magnitude_label": "Observed order value",
            "magnitude_value": (
                sum(observed_order_values) if observed_order_values else None
            ),
            "magnitude_unit": "USD",
            "production_status": "Evidence available",
        }
    else:
        modeled_economics = summary.get("modeled_business_economics") or {}
        modeled_orders = modeled_economics.get("recovered_orders_per_month")
        if modeled_orders is not None:
            outcome = {
                "evidence_type": "MODELED",
                "primary_metric_label": "Modeled recovered orders / month",
                "primary_metric_value": modeled_orders,
                "primary_metric_unit": "orders",
                "magnitude_label": "Modeled recovered contribution / month",
                "magnitude_value": value["modeled"][
                    "recovered_contribution_usd"
                ],
                "magnitude_unit": "USD",
                "production_status": "Not observed",
            }
        else:
            outcome = {
                "evidence_type": "UNKNOWN",
                "primary_metric_label": "Business outcome",
                "primary_metric_value": None,
                "primary_metric_unit": None,
                "magnitude_label": "Outcome magnitude",
                "magnitude_value": None,
                "magnitude_unit": None,
                "production_status": "Not available",
            }

    confidence = (
        summary.get("evidence_confidence")
        or assessment.get("evidence_confidence")
        or "UNKNOWN"
    )
    confidence = str(confidence).replace("_", " ").upper()
    if confidence not in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}:
        confidence = "UNKNOWN"

    action = act_view(summary)
    required_evidence = action["required_evidence"]
    required_work = action["required_work"]
    next_step = (
        required_evidence[0]
        if required_evidence
        else required_work[0]
        if required_work
        else None
    )
    customer_net_value = value["decision_grade"][
        "customer_net_economic_value_usd"
    ]
    customer_cost_completeness = (
        (summary.get("economic_value") or {}).get("customer_cost_completeness")
    )
    incremental_economics_status = (
        (summary.get("incremental_economics") or {}).get("economics_status")
    )
    customer_economics_status = (
        "Established"
        if customer_net_value is not None
        and customer_cost_completeness == "complete"
        and incremental_economics_status == "incremental_net_value_established"
        else "Not established"
    )
    cost_evidence_source = runtime_cost.get("evidence_source") or {}
    cost_evidence_status = str(
        cost_evidence_source.get("evidence_status") or "unknown"
    ).replace("_", " ").upper()
    business_value_status = (
        "MODELED" if value_evidence_type == "MODELED" else "UNKNOWN"
    )

    return {
        "context": {
            "workload": workload_name,
            "run_id": summary.get("run_id") or UNAVAILABLE,
            "period": period_label,
            "evidence_status": (
                f"Azure cost {cost_evidence_status} · "
                f"Business value {business_value_status} · "
                f"Outcome {outcome['evidence_type']}"
            ),
            "customer_economics_status": customer_economics_status,
        },
        "work": {
            "workload": workload_name,
            "objective": summary.get("business_objective")
            or VALUE_PULSE_OBJECTIVE,
            "accepted_work_definition": VALUE_PULSE_ACCEPTED_WORK,
        },
        "measure": {
            "accepted_work_count": accepted_count,
            "accepted_work_rate": accepted_rate,
            "system_cost_usd": runtime_cost.get(
                "allocated_azure_runtime_cost_usd"
            ),
            "system_cost_period": period_label,
            "system_cost_evidence": cost_evidence_status,
            "cost_per_accepted_work_usd": direct_cost_per_accepted_work,
            "cost_per_accepted_work_basis": (
                "Run inference cost"
                if direct_cost_per_accepted_work is not None
                else "Not established"
            ),
        },
        "outcome": outcome,
        "value": {
            "economic_value_label": economic_value_label,
            "economic_value_usd": economic_value_amount,
            "value_multiple_label": value_multiple_label,
            "value_multiple": value_multiple,
            "value_evidence_type": value_evidence_type,
            "evidence_confidence": confidence,
            "customer_economics_status": customer_economics_status,
        },
        "action": {
            "selected_action": action["selected_action"],
            "rationale": action["action_rationale"],
            "next_step": next_step,
        },
    }


def interaction_table_rows(interactions: list[dict]) -> list[dict]:
    """Flatten interactions to a compact table projection (no nested dump)."""

    rows = []
    for record in interactions:
        execution = record.get("execution") or {}
        acceptance = record.get("acceptance") or {}
        pilot = record.get("pilot") or {}
        outcome = record.get("business_outcome") or {}
        case = record.get("case") or {}

        rows.append(
            {
                "interaction_id": record.get("interaction_id"),
                "category": case.get("category"),
                "accepted": acceptance.get("accepted"),
                "tokens": execution.get("total_tokens"),
                "model_cost_usd": execution.get("model_cost_usd"),
                "latency_ms": execution.get("latency_ms"),
                "tool_call_count": execution.get("tool_call_count"),
                "assignment": pilot.get("assignment"),
                "exposure": pilot.get("exposure"),
                "order_completed": outcome.get("order_completed"),
                "order_value_usd": outcome.get("order_value_usd"),
            }
        )
    return rows
