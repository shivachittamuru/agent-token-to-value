"""Portfolio Action records — select the action for the primary deficit.

Eligibility (from the Decision Gate Record) and selection are different steps.
This module identifies the workload's primary decision deficit and selects the
canonical action that addresses it, then validates that the selected action is
actually eligible. Decision gates constrain selection: an ineligible action can
never be selected, and strong modeled economics never force a SCALE.
"""

from __future__ import annotations

CANONICAL_ACTIONS = (
    "scale",
    "sustain",
    "optimize",
    "prove",
    "restructure",
    "pause",
    "retire",
)


def _determine_deficit_and_action(
    workload_assessment: dict,
    decision_gates: dict,
) -> tuple[str, str]:
    gates = decision_gates["gates"]
    eligible = decision_gates["eligible_actions"]

    business = workload_assessment["business_outcome_status"]
    incrementality = workload_assessment["incrementality_status"]
    economic_value = workload_assessment["economic_value_status"]
    incremental_econ = workload_assessment["incremental_economics_status"]

    # Optional explicit hints; conservative defaults keep behaviour honest.
    continuing_rationale = workload_assessment.get("continuing_rationale", True)
    near_term_work = workload_assessment.get("near_term_work_available", True)
    execution_constraint = workload_assessment.get("execution_constraint", False)

    # 1. Non-compensable mandatory blocker (strategic or RAI/risk/control only).
    mandatory_failed = (
        gates["strategic_mandatory_gate"]["status"] == "fail"
        or gates["rai_risk_control_gate"]["status"] == "fail"
    )
    if mandatory_failed:
        if near_term_work and "restructure" in eligible:
            return "control", "restructure"
        return "mandatory_blocker", "pause"

    # 2. Structural / commercial / control deficit.
    if gates["commercial_fit_gate"]["status"] == "fail":
        return "structural", "restructure"

    # 3. No continuing rationale.
    if not continuing_rationale:
        return "no_continuing_rationale", "retire"

    # 4. Scale-ready: established next-dollar economics + required gates pass.
    scale_ready = (
        gates["value_gate"]["status"] == "pass"
        and gates["evidence_gate"]["status"] == "pass"
        and gates["incremental_economics_gate"]["status"] == "pass"
        and gates["resilience_gate"]["status"] == "pass"
        and incremental_econ == "incremental_net_value_established"
    )
    if scale_ready:
        return "none", "scale"

    # 5. Execution deficit: value established but execution is the constraint.
    value_established = (
        economic_value == "incremental_value_established"
        or business == "observed"
    )
    if value_established and execution_constraint:
        return "execution", "optimize"

    # 6. Evidence deficit: business/causal/incremental value not established.
    if (
        business == "unknown"
        or incrementality == "unknown"
        or incremental_econ != "incremental_net_value_established"
    ):
        return "evidence", "prove"

    # 7. No justified near-term work.
    if not near_term_work:
        return "no_near_term_work", "pause"

    # 8. Current operation justified without expansion.
    return "operation_justified", "sustain"


def _required_work(action: str) -> list[str]:
    return {
        "prove": [
            "measure real AI-eligible unanswered demand",
            "assign treatment/control",
            "link downstream business outcomes",
            "measure Total Relevant Customer Cost",
            "capture realistic-volume operating evidence",
        ],
        "scale": [
            "execute the defined increment",
            "instrument incremental value and cost at the new scale",
        ],
        "optimize": [
            "reduce cost per Accepted Work, retries, and latency",
            "improve execution efficiency where it constrains value",
        ],
        "restructure": [
            "revise the commercial, operating, ownership, or control structure",
        ],
        "sustain": [
            "continue current operation without material expansion",
        ],
        "pause": [
            "hold further investment and define a reassessment trigger",
        ],
        "retire": [
            "wind down continuing investment or operation",
        ],
    }[action]


def _resource_request(action: str) -> str:
    return {
        "prove": "bounded pilot instrumentation and business-outcome measurement",
        "scale": (
            "qualitative expansion resourcing; explicit budget supplied by the "
            "decision owner"
        ),
        "optimize": (
            "qualitative execution-improvement effort; explicit staffing "
            "supplied by the decision owner"
        ),
        "restructure": (
            "qualitative structural-change effort; explicit scope supplied by "
            "the decision owner"
        ),
        "sustain": "continue current operating resourcing",
        "pause": "no additional near-term investment",
        "retire": "wind-down resourcing",
    }[action]


def _reassessment_trigger(action: str) -> str:
    if action == "prove":
        return (
            "pilot evidence sufficient to evaluate incremental conversion, "
            "incremental contribution, Total Relevant Customer Cost, "
            "Incremental Net Economic Value, and material operational/control "
            "issues"
        )
    return "evidence materially changes gate readiness or economics"


def _conditions_that_change_action(action: str) -> list[dict]:
    if action == "prove":
        return [
            {
                "from": "prove",
                "to": "scale",
                "condition": (
                    "incremental economics attractive and required gates pass"
                ),
            },
            {
                "from": "prove",
                "to": "optimize",
                "condition": "value established but execution is the primary constraint",
            },
            {
                "from": "prove",
                "to": "restructure",
                "condition": "structural/commercial/control issues dominate",
            },
            {
                "from": "prove",
                "to": "pause",
                "condition": (
                    "evidence cannot currently be obtained or a blocker "
                    "prevents justified work"
                ),
            },
            {
                "from": "prove",
                "to": "retire",
                "condition": (
                    "evidence removes the continuing rationale and no "
                    "strategic/mandatory/dependency rationale remains"
                ),
            },
        ]
    return [
        {
            "from": action,
            "to": "reassess",
            "condition": "evidence, economics, or gate readiness changes materially",
        }
    ]


def _action_rationale(
    action: str, deficit: str, workload_assessment: dict
) -> str:
    if action == "prove":
        scope = workload_assessment.get("technical_evidence_scope", "regression")
        scope_phrase = (
            "simulated workload"
            if scope == "simulation"
            else "regression workload"
        )
        return (
            f"Technical behavior is established for the {scope_phrase} and "
            "modeled economics appear attractive, but real business outcomes, "
            "incrementality, and next-dollar economics are not established. "
            "Scale is currently ineligible, so a bounded pilot is authorized "
            "to reduce the decision-critical uncertainty."
        )
    return (
        f"Selected {action} to address the primary {deficit} deficit, "
        f"consistent with the decision gates and workload assessment."
    )


def build_portfolio_action_record(
    *,
    workload_id: str,
    decision_id: str | None,
    decision_context: str,
    workload_assessment: dict,
    decision_gates: dict,
    decision_owner: str | None = None,
    decision_date: str | None = None,
) -> dict:
    """Select the portfolio action that addresses the primary decision deficit.

    The selected action is validated against the Decision Gate Record's
    ``eligible_actions`` and fails loudly if an ineligible action is chosen.
    """

    primary_decision_deficit, selected_action = _determine_deficit_and_action(
        workload_assessment, decision_gates
    )

    if selected_action not in decision_gates["eligible_actions"]:
        raise ValueError(
            f"Selected action {selected_action!r} is not eligible: "
            f"{decision_gates['eligible_actions']}"
        )

    required_evidence = (
        workload_assessment.get("next_evidence_priorities")
        or workload_assessment.get("decision_gaps")
        or []
    )

    return {
        "workload_id": workload_id,
        "decision_id": decision_id,
        "decision_context": decision_context,
        "selected_action": selected_action,
        "primary_decision_deficit": primary_decision_deficit,
        "action_rationale": _action_rationale(
            selected_action, primary_decision_deficit, workload_assessment
        ),
        "required_work": _required_work(selected_action),
        "required_evidence": list(required_evidence),
        "resource_request": _resource_request(selected_action),
        # Never fabricated; Unknown until an owner is explicitly supplied.
        "decision_owner": decision_owner,
        "decision_date": decision_date,
        "reassessment_trigger": _reassessment_trigger(selected_action),
        "conditions_that_change_action": _conditions_that_change_action(
            selected_action
        ),
    }
