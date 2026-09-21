import json

import pytest

from foundry_prompt_agent.decision_gates import (
    CANONICAL_ACTIONS,
    build_decision_gate_record,
)

CONTEXT = "Determine what portfolio actions are supportable by the current evidence."


def workload_assessment(
    technical="established_regression",
    business="unknown",
    incrementality="unknown",
    economic_value="modeled_only",
) -> dict:
    return {
        "technical_performance_status": technical,
        "business_outcome_status": business,
        "incrementality_status": incrementality,
        "economic_value_status": economic_value,
    }


def incremental_economics(status="not_established") -> dict:
    return {"economics_status": status}


def value_resilience(
    scope="modeled_scenario", status="not_classified"
) -> dict:
    return {"resilience_scope": scope, "resilience_status": status}


def build(**overrides) -> dict:
    kwargs = {
        "workload_id": "contoso-demand-recovery",
        "decision_id": None,
        "decision_context": CONTEXT,
        "workload_assessment": workload_assessment(),
        "incremental_economics": incremental_economics(),
        "value_resilience": value_resilience(),
        "commercial_fit": None,
        "governance": None,
        "strategic_context": None,
    }
    kwargs.update(overrides)
    return build_decision_gate_record(**kwargs)


def ineligible_names(record: dict) -> set[str]:
    return {entry["action"] for entry in record["ineligible_actions"]}


def test_unknown_stays_unknown():
    record = build()

    assert record["gates"]["strategic_mandatory_gate"]["status"] == "unknown"
    assert record["gates"]["commercial_fit_gate"]["status"] == "unknown"
    assert record["gates"]["rai_risk_control_gate"]["status"] == "unknown"
    assert record["gates"]["incremental_economics_gate"]["status"] == "unknown"


def test_modeled_value_not_promoted_to_incremental():
    record = build()
    value = record["gates"]["value_gate"]

    assert value["status"] == "conditional"
    assert "modeled" in value["rationale"].lower()


def test_no_pilot_evidence_constrains_scale_eligibility():
    record = build(
        workload_assessment=workload_assessment(incrementality="unknown")
    )

    assert "scale" not in record["eligible_actions"]
    assert "scale" in ineligible_names(record)


def test_not_established_incremental_economics_constrains_scale():
    record = build(incremental_economics=incremental_economics("not_established"))

    assert "scale" not in record["eligible_actions"]


def test_modeled_resilience_preserved():
    record = build()
    resilience = record["gates"]["resilience_gate"]

    assert resilience["status"] == "conditional"
    assert "modeled scenario" in resilience["rationale"].lower()


def test_absent_commercial_fit_is_unknown():
    record = build(commercial_fit=None)

    assert record["gates"]["commercial_fit_gate"]["status"] == "unknown"


def test_absent_governance_is_unknown():
    record = build(governance=None)

    assert record["gates"]["rai_risk_control_gate"]["status"] == "unknown"


def test_mandatory_governance_failure_blocks_deployment_regardless_of_economics():
    # Even with fully established economics, a failed mandatory control blocks
    # deployment/expansion actions.
    record = build(
        workload_assessment=workload_assessment(
            business="observed",
            incrementality="established",
            economic_value="incremental_value_established",
        ),
        incremental_economics=incremental_economics(
            "incremental_net_value_established"
        ),
        governance={
            "mandatory_control_failed": True,
            "rationale": "Required safety control failing.",
        },
    )

    assert record["gates"]["rai_risk_control_gate"]["status"] == "fail"
    assert "scale" not in record["eligible_actions"]
    assert "sustain" not in record["eligible_actions"]
    assert set(record["eligible_actions"]) == {"pause", "retire"}


def test_no_composite_score_field():
    record = build()
    serialized = json.dumps(record).lower()

    assert "score" not in serialized
    assert "confidence" not in serialized


def test_no_final_or_recommended_action_field():
    record = build()

    assert "recommended_action" not in record
    assert "portfolio_action" not in record
    assert "final_action" not in record
    assert record["action_selected"] is False


def test_canonical_actions_represented_separately():
    record = build()
    represented = set(record["eligible_actions"]) | ineligible_names(record)

    assert represented == set(CANONICAL_ACTIONS)


def test_scale_currently_ineligible():
    record = build()

    assert "scale" in ineligible_names(record)


def test_decision_context_preserved():
    record = build()

    assert record["decision_context"] == CONTEXT


def test_gate_rationales_preserved():
    record = build()

    for gate in record["gates"].values():
        assert gate["rationale"]
        assert isinstance(gate["rationale"], str)
