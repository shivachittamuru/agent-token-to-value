"""Pure presentation helpers for the Value-to-Action dashboard.

These functions only map already-stored run-package fields into display-ready
structures. They never recalculate economics or decision logic, never call the
agent/Azure/Foundry, and never invent values: missing optional fields render as
Unknown / unavailable, and Unknown statuses do not get a fabricated scope.
"""

from __future__ import annotations

UNAVAILABLE = "—"

JOURNEY_STAGES = ("MEASURE", "PROVE", "VALUE", "TEST", "DECIDE", "ACT")


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
    """Three separate value layers; synthetic never feeds decision-grade."""

    modeled_economics = summary.get("modeled_business_economics") or {}
    economic_value = summary.get("economic_value") or {}
    synthetic = summary.get("synthetic_economics")

    incremental = summary.get("incremental_economics") or {}
    incremental_established = (
        incremental.get("economics_status")
        == "incremental_net_value_established"
    )

    return {
        "modeled": {
            "recovered_contribution_usd": modeled_economics.get(
                "recovered_contribution_per_month"
            ),
            "ai_value_multiple": modeled_economics.get("ai_value_multiple"),
            "cost_completeness": economic_value.get("cost_completeness"),
        },
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
