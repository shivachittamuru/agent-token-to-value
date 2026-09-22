"""Decision Gate records — independent DECIDE-phase constraints.

Decision gates are evaluated independently. There is no composite score, no
averaging of gate states, and strong economics never numerically compensate
for a failed mandatory gate. This slice determines which canonical portfolio
actions the current evidence can *support* (eligibility); it never selects a
final portfolio action.
"""

from __future__ import annotations

GATE_PASS = "pass"
GATE_CONDITIONAL = "conditional"
GATE_FAIL = "fail"
GATE_UNKNOWN = "unknown"
GATE_NOT_APPLICABLE = "not_applicable"

CANONICAL_ACTIONS = (
    "scale",
    "sustain",
    "optimize",
    "prove",
    "restructure",
    "pause",
    "retire",
)

# Actions that continue, expand, or (re)deploy the workload. A failed mandatory
# gate blocks all of these regardless of economic attractiveness.
DEPLOYMENT_OR_EXPANSION_ACTIONS = (
    "scale",
    "sustain",
    "optimize",
    "prove",
    "restructure",
)


def _gate(status: str, rationale: str) -> dict:
    return {"status": status, "rationale": rationale}


def _strategic_mandatory_gate(strategic_context: dict | None) -> dict:
    if strategic_context and strategic_context.get("status"):
        return _gate(
            strategic_context["status"],
            strategic_context.get("rationale", "Explicit strategic context."),
        )
    return _gate(GATE_UNKNOWN, "No strategic/mandatory context recorded.")


def _value_gate(economic_value_status: str) -> dict:
    if economic_value_status == "incremental_value_established":
        return _gate(GATE_PASS, "Evidence-backed incremental value established.")
    if economic_value_status == "observed_not_incremental":
        return _gate(
            GATE_CONDITIONAL,
            "Business value observed but not yet incremental.",
        )
    return _gate(
        GATE_CONDITIONAL,
        "Modeled scenario value only; not evidence-backed incremental value.",
    )


def _evidence_gate(workload_assessment: dict) -> dict:
    technical = workload_assessment["technical_performance_status"]
    scope = workload_assessment.get("technical_evidence_scope", "regression")
    business = workload_assessment["business_outcome_status"]
    incrementality = workload_assessment["incrementality_status"]

    if (
        technical == "established"
        and business == "observed"
        and incrementality == "established"
    ):
        return _gate(GATE_PASS, "Technical, business, and causal evidence established.")
    if business == "unknown" or incrementality == "unknown":
        return _gate(
            GATE_CONDITIONAL,
            f"Technical evidence strong for the {scope} workload; downstream "
            "business and causal evidence remain Unknown.",
        )
    return _gate(GATE_CONDITIONAL, "Partial evidence across dimensions.")


def _resilience_gate(value_resilience: dict) -> dict:
    scope = value_resilience["resilience_scope"]
    status = value_resilience["resilience_status"]
    if scope == "modeled_scenario":
        return _gate(
            GATE_CONDITIONAL,
            f"Modeled scenario resilience only; classification={status}.",
        )
    return _gate(GATE_UNKNOWN, "Resilience evidence not established.")


def _incremental_economics_gate(incremental_economics: dict) -> dict:
    if (
        incremental_economics["economics_status"]
        == "incremental_net_value_established"
    ):
        return _gate(GATE_PASS, "Incremental (next-dollar) net economic value established.")
    return _gate(GATE_UNKNOWN, "Next-dollar incremental economics not established.")


def _commercial_fit_gate(commercial_fit: dict | None) -> dict:
    if commercial_fit and commercial_fit.get("status"):
        return _gate(
            commercial_fit["status"],
            commercial_fit.get("rationale", "Explicit commercial-fit evidence."),
        )
    return _gate(GATE_UNKNOWN, "No commercial-fit evidence recorded.")


def _rai_risk_control_gate(governance: dict | None) -> dict:
    if governance:
        if governance.get("mandatory_control_failed") is True:
            return _gate(
                GATE_FAIL,
                governance.get("rationale", "Mandatory control failed."),
            )
        if governance.get("status"):
            return _gate(
                governance["status"],
                governance.get("rationale", "Explicit governance assessment."),
            )
    return _gate(
        GATE_UNKNOWN,
        "No responsible-AI/risk/control decision-gate assessment recorded.",
    )


def build_decision_gate_record(
    *,
    workload_id: str,
    decision_id: str | None,
    decision_context: str,
    workload_assessment: dict,
    incremental_economics: dict,
    value_resilience: dict,
    commercial_fit: dict | None = None,
    governance: dict | None = None,
    strategic_context: dict | None = None,
) -> dict:
    """Build a Decision Gate record: independent gates plus action eligibility.

    No composite score is produced and no final portfolio action is selected.
    A failed mandatory gate blocks deployment/expansion actions and cannot be
    offset by economic attractiveness.
    """

    gates = {
        "strategic_mandatory_gate": _strategic_mandatory_gate(strategic_context),
        "value_gate": _value_gate(
            workload_assessment["economic_value_status"]
        ),
        "evidence_gate": _evidence_gate(workload_assessment),
        "resilience_gate": _resilience_gate(value_resilience),
        "incremental_economics_gate": _incremental_economics_gate(
            incremental_economics
        ),
        "commercial_fit_gate": _commercial_fit_gate(commercial_fit),
        "rai_risk_control_gate": _rai_risk_control_gate(governance),
    }

    blocking_gates = [
        name for name, gate in gates.items() if gate["status"] == GATE_FAIL
    ]
    conditional_gates = [
        name for name, gate in gates.items() if gate["status"] == GATE_CONDITIONAL
    ]
    unknown_gates = [
        name for name, gate in gates.items() if gate["status"] == GATE_UNKNOWN
    ]

    mandatory_failed = (
        gates["strategic_mandatory_gate"]["status"] == GATE_FAIL
        or gates["rai_risk_control_gate"]["status"] == GATE_FAIL
    )

    scale_ready = (
        gates["value_gate"]["status"] == GATE_PASS
        and gates["evidence_gate"]["status"] == GATE_PASS
        and gates["incremental_economics_gate"]["status"] == GATE_PASS
        and gates["resilience_gate"]["status"] == GATE_PASS
    )

    eligible_actions: list[str] = []
    ineligible_actions: list[dict] = []

    for action in CANONICAL_ACTIONS:
        if mandatory_failed and action in DEPLOYMENT_OR_EXPANSION_ACTIONS:
            ineligible_actions.append(
                {
                    "action": action,
                    "rationale": (
                        "Mandatory gate failed; deployment/expansion blocked "
                        "(non-compensable by economics)."
                    ),
                }
            )
        elif action == "scale" and not scale_ready:
            ineligible_actions.append(
                {
                    "action": "scale",
                    "rationale": (
                        "Evidence-backed incremental value and next-dollar "
                        "economics not established."
                    ),
                }
            )
        else:
            eligible_actions.append(action)

    return {
        "workload_id": workload_id,
        "decision_id": decision_id,
        "decision_context": decision_context,
        "gates": gates,
        "blocking_gates": blocking_gates,
        "conditional_gates": conditional_gates,
        "unknown_gates": unknown_gates,
        "eligible_actions": eligible_actions,
        "ineligible_actions": ineligible_actions,
        # Eligibility only; the final portfolio action is never selected here.
        "action_selected": False,
    }
