import json

import pytest

from foundry_prompt_agent.portfolio_action import (
    build_portfolio_action_record,
)

CONTEXT = "Determine what portfolio action is justified by the current evidence."

ALL_ACTIONS = ["sustain", "optimize", "prove", "restructure", "pause", "retire"]


def assessment(
    technical="established",
    business="unknown",
    incrementality="unknown",
    economic_value="modeled_only",
    incremental_economics="not_established",
    technical_evidence_scope="regression",
    **hints,
) -> dict:
    base = {
        "technical_performance_status": technical,
        "technical_evidence_scope": technical_evidence_scope,
        "business_outcome_status": business,
        "incrementality_status": incrementality,
        "economic_value_status": economic_value,
        "incremental_economics_status": incremental_economics,
        "next_evidence_priorities": [
            "actual eligible-demand baseline",
            "treatment/control conversion",
        ],
        "decision_gaps": ["real business outcomes"],
    }
    base.update(hints)
    return base


def gates(
    value="conditional",
    evidence="conditional",
    resilience="conditional",
    incremental="unknown",
    commercial="unknown",
    rai="unknown",
    strategic="unknown",
    eligible=None,
) -> dict:
    statuses = {
        "strategic_mandatory_gate": strategic,
        "value_gate": value,
        "evidence_gate": evidence,
        "resilience_gate": resilience,
        "incremental_economics_gate": incremental,
        "commercial_fit_gate": commercial,
        "rai_risk_control_gate": rai,
    }
    gate_map = {name: {"status": s, "rationale": "r"} for name, s in statuses.items()}
    blocking = [n for n, g in gate_map.items() if g["status"] == "fail"]
    return {
        "gates": gate_map,
        "blocking_gates": blocking,
        "conditional_gates": [
            n for n, g in gate_map.items() if g["status"] == "conditional"
        ],
        "unknown_gates": [
            n for n, g in gate_map.items() if g["status"] == "unknown"
        ],
        "eligible_actions": eligible if eligible is not None else list(ALL_ACTIONS),
        "ineligible_actions": [],
        "action_selected": False,
    }


def build(**overrides) -> dict:
    kwargs = {
        "workload_id": "contoso-demand-recovery",
        "decision_id": None,
        "decision_context": CONTEXT,
        "workload_assessment": assessment(),
        "decision_gates": gates(),
        "decision_owner": None,
        "decision_date": "2026-09-21T00:00:00+00:00",
    }
    kwargs.update(overrides)
    return build_portfolio_action_record(**kwargs)


def scale_ready_assessment() -> dict:
    return assessment(
        business="observed",
        incrementality="established",
        economic_value="incremental_value_established",
        incremental_economics="incremental_net_value_established",
    )


def scale_ready_gates() -> dict:
    return gates(
        value="pass",
        evidence="pass",
        resilience="pass",
        incremental="pass",
        eligible=["scale", *ALL_ACTIONS],
    )


def test_current_contoso_selects_prove():
    record = build()

    assert record["selected_action"] == "prove"
    assert record["primary_decision_deficit"] == "evidence"


def test_selected_action_must_be_eligible():
    # Structural deficit points at restructure, but it is not eligible here.
    with pytest.raises(ValueError):
        build(
            workload_assessment=assessment(),
            decision_gates=gates(
                commercial="fail",
                eligible=["prove", "pause", "retire"],
            ),
        )


def test_high_modeled_economics_never_selects_scale():
    record = build(
        workload_assessment=assessment(economic_value="modeled_only"),
        decision_gates=gates(),
    )

    assert record["selected_action"] != "scale"
    assert record["selected_action"] == "prove"


def test_evidence_deficit_maps_to_prove():
    record = build(workload_assessment=assessment(business="unknown"))

    assert record["selected_action"] == "prove"


def test_execution_deficit_can_select_optimize():
    record = build(
        workload_assessment=assessment(
            business="observed",
            incrementality="established",
            economic_value="incremental_value_established",
            incremental_economics="not_established",
            execution_constraint=True,
        ),
        decision_gates=gates(value="pass", evidence="pass"),
    )

    assert record["selected_action"] == "optimize"
    assert record["primary_decision_deficit"] == "execution"


def test_structural_deficit_can_select_restructure():
    record = build(
        decision_gates=gates(commercial="fail"),
    )

    assert record["selected_action"] == "restructure"
    assert record["primary_decision_deficit"] == "structural"


def test_justified_operation_can_select_sustain():
    record = build(
        workload_assessment=assessment(
            business="observed",
            incrementality="established",
            economic_value="incremental_value_established",
            incremental_economics="incremental_net_value_established",
        ),
        # Resilience not passed, so not scale-ready; operation still justified.
        decision_gates=gates(value="pass", evidence="pass", incremental="pass"),
    )

    assert record["selected_action"] == "sustain"


def test_blocker_can_select_pause():
    record = build(
        workload_assessment=assessment(
            business="observed",
            incrementality="established",
            economic_value="incremental_value_established",
            incremental_economics="incremental_net_value_established",
            near_term_work_available=False,
        ),
        decision_gates=gates(value="pass", evidence="pass", incremental="pass"),
    )

    assert record["selected_action"] == "pause"


def test_absent_rationale_can_select_retire():
    record = build(
        workload_assessment=assessment(continuing_rationale=False),
    )

    assert record["selected_action"] == "retire"


def test_scale_requires_established_incremental_and_gates():
    record = build(
        workload_assessment=scale_ready_assessment(),
        decision_gates=scale_ready_gates(),
    )

    assert record["selected_action"] == "scale"
    assert record["primary_decision_deficit"] == "none"


def test_owner_remains_unknown_when_absent():
    record = build(decision_owner=None)

    assert record["decision_owner"] is None


def test_no_fabricated_budget_or_headcount():
    record = build()

    assert not any(ch.isdigit() for ch in record["resource_request"])


def test_reassessment_trigger_present():
    record = build()

    assert record["reassessment_trigger"]
    assert "incremental" in record["reassessment_trigger"].lower()


def test_action_rationale_traceable_to_evidence():
    record = build()
    rationale = record["action_rationale"].lower()

    assert "regression" in rationale
    assert "scale" in rationale


def test_simulation_action_rationale_has_no_regression_wording():
    record = build(
        workload_assessment=assessment(technical_evidence_scope="simulation")
    )
    rationale = record["action_rationale"].lower()

    assert "regression" not in rationale
    assert "simulated workload" in rationale


def test_synthetic_evidence_keeps_action_prove():
    record = build(
        workload_assessment=assessment(
            business="observed",
            incrementality="established",
            business_evidence_scope="simulation",
            incrementality_evidence_scope="simulation",
        )
    )

    assert record["selected_action"] == "prove"
    rationale = record["action_rationale"].lower()
    assert "synthetic experiment" in rationale
    assert "realized" not in rationale
    assert "production incrementality" in rationale


def test_no_composite_score_field():
    record = build()
    serialized = json.dumps(record).lower()

    assert "score" not in serialized
    assert "confidence" not in serialized


def test_prove_not_auto_selected_when_scale_unavailable_but_structural():
    # Scale unavailable, but the dominant deficit is structural, not evidence.
    record = build(decision_gates=gates(commercial="fail"))

    assert record["selected_action"] == "restructure"
    assert record["selected_action"] != "prove"
