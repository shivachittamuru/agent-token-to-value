import json

import pytest

from foundry_prompt_agent.workload_assessment import (
    ASSESSMENT_INCOMPLETE,
    build_workload_assessment,
)


def execution_economics(cost_completeness="partial") -> dict:
    return {
        "known_direct_execution_cost_usd": 0.078,
        "cost_completeness": cost_completeness,
    }


def economic_value(value_evidence_status="modeled_only") -> dict:
    return {"value_evidence_status": value_evidence_status}


def incremental_economics(economics_status="not_established") -> dict:
    return {"economics_status": economics_status}


def value_resilience(
    resilience_scope="modeled_scenario", resilience_status="not_classified"
) -> dict:
    return {
        "resilience_scope": resilience_scope,
        "resilience_status": resilience_status,
    }


def business_outcome_records(accepted=True, with_evidence=False) -> list[dict]:
    downstream = {
        "customer_engaged_after_response": None,
        "order_completed": None,
        "order_id": None,
        "order_value_usd": None,
        "incremental_order": None,
        "counterfactual_method": None,
        "outcome_evidence_source": None,
        "outcome_observed_at_utc": None,
    }
    if with_evidence:
        downstream["order_completed"] = True
        downstream["outcome_evidence_source"] = "pos_system"

    return [
        {"interaction_id": f"i{n}", "accepted": accepted, **downstream}
        for n in range(3)
    ]


def pilot_evidence_records(assignment=None) -> list[dict]:
    return [
        {"interaction_id": f"i{n}", "assignment": assignment}
        for n in range(3)
    ]


def build(**overrides) -> dict:
    kwargs = {
        "workload_id": "contoso-demand-recovery",
        "execution_economics": execution_economics(),
        "economic_value": economic_value(),
        "incremental_economics": incremental_economics(),
        "value_resilience": value_resilience(),
        "business_outcome_records": business_outcome_records(),
        "pilot_evidence_records": pilot_evidence_records(),
    }
    kwargs.update(overrides)
    return build_workload_assessment(**kwargs)


def test_current_contoso_assessment():
    record = build()

    assert record["technical_performance_status"] == "established"
    assert record["technical_evidence_scope"] == "regression"
    assert record["execution_cost_status"] == "partial"
    assert record["business_outcome_status"] == "unknown"
    assert record["incrementality_status"] == "unknown"
    assert record["economic_value_status"] == "modeled_only"
    assert record["incremental_economics_status"] == "not_established"
    assert record["resilience_scope"] == "modeled_scenario"
    assert record["resilience_status"] == "not_classified"


def test_regression_scope_preserved():
    record = build(run_mode="regression")

    assert record["technical_evidence_scope"] == "regression"
    assert any("regression suite" in claim for claim in record["established_claims"])


def test_simulation_scope_preserved():
    record = build(run_mode="simulation")

    assert record["technical_performance_status"] == "established"
    assert record["technical_evidence_scope"] == "simulation"
    assert any(
        "simulated workload" in claim for claim in record["established_claims"]
    )


def test_simulation_assessment_has_no_regression_wording():
    record = build(run_mode="simulation")

    for claim in record["established_claims"]:
        assert "regression" not in claim.lower()


def test_strong_technical_evidence_does_not_promote_business():
    # All accepted, but downstream and economic evidence stay weak.
    record = build(business_outcome_records=business_outcome_records(accepted=True))

    assert record["technical_performance_status"] == "established"
    assert record["business_outcome_status"] == "unknown"
    assert record["economic_value_status"] == "modeled_only"


def test_business_outcomes_all_unknown_is_unknown():
    record = build(
        business_outcome_records=business_outcome_records(with_evidence=False)
    )

    assert record["business_outcome_status"] == "unknown"


def test_observed_business_evidence_changes_status():
    record = build(
        business_outcome_records=business_outcome_records(with_evidence=True)
    )

    assert record["business_outcome_status"] == "observed"


def test_no_pilot_evidence_keeps_incrementality_unknown():
    record = build(pilot_evidence_records=pilot_evidence_records(assignment=None))

    assert record["incrementality_status"] == "unknown"


def test_modeled_economic_value_preserved():
    record = build(economic_value=economic_value("modeled_only"))

    assert record["economic_value_status"] == "modeled_only"


def test_incremental_economics_not_established_preserved():
    record = build(
        incremental_economics=incremental_economics("not_established")
    )

    assert record["incremental_economics_status"] == "not_established"


def test_modeled_resilience_remains_modeled_not_classified():
    record = build()

    assert record["resilience_scope"] == "modeled_scenario"
    assert record["resilience_status"] == "not_classified"


def test_claim_lists_remain_separate():
    record = build()

    established = set(record["established_claims"])
    modeled = set(record["modeled_claims"])
    unknown = set(record["unknown_claims"])

    assert established and modeled and unknown
    assert established.isdisjoint(modeled)
    assert established.isdisjoint(unknown)
    assert modeled.isdisjoint(unknown)


def test_no_composite_score_field():
    record = build()
    serialized = json.dumps(record).lower()

    assert "score" not in serialized
    assert "confidence" not in serialized


def test_no_portfolio_action_field():
    record = build()
    serialized = json.dumps(record).lower()

    for action in ("scale", "sustain", "optimize", "restructure", "retire"):
        assert action not in serialized
    assert "portfolio_action" not in record


def test_decision_gaps_remain_explicit():
    record = build()

    assert isinstance(record["decision_gaps"], list)
    assert record["decision_gaps"]
    assert "next-dollar economics" in record["decision_gaps"]


def test_assessment_status_is_neutral():
    record = build()

    assert record["assessment_status"] == ASSESSMENT_INCOMPLETE


def _simulation_business_records() -> list[dict]:
    downstream = {
        "customer_engaged_after_response": True,
        "order_completed": True,
        "order_id": "sim-order-i0",
        "order_value_usd": 8.0,
        "incremental_order": None,
        "counterfactual_method": "randomized_synthetic_control",
        "outcome_evidence_source": "synthetic_simulation",
        "outcome_observed_at_utc": "2026-01-01T00:10:00+00:00",
    }
    return [
        {"interaction_id": f"i{n}", "accepted": True, **downstream}
        for n in range(3)
    ]


def _simulation_pilot_records() -> list[dict]:
    return [
        {
            "interaction_id": f"i{n}",
            "assignment": "treatment" if n % 2 == 0 else "control",
            "exposure": "ai_exposed_to_simulated_customer",
            "evidence_mode": "synthetic_simulation",
            "simulated": True,
        }
        for n in range(3)
    ]


def simulation_assessment(**overrides) -> dict:
    kwargs = {
        "workload_id": "contoso-demand-recovery",
        "execution_economics": execution_economics(),
        "economic_value": economic_value(),
        "incremental_economics": incremental_economics(),
        "value_resilience": value_resilience(),
        "business_outcome_records": _simulation_business_records(),
        "pilot_evidence_records": _simulation_pilot_records(),
        "run_mode": "simulation",
        "synthetic_experiment": {"treatment_count": 2, "control_count": 1},
    }
    kwargs.update(overrides)
    return build_workload_assessment(**kwargs)


def test_simulation_business_status_observed_scope_simulation():
    record = simulation_assessment()

    assert record["business_outcome_status"] == "observed"
    assert record["business_evidence_scope"] == "simulation"


def test_simulation_incrementality_established_scope_simulation():
    record = simulation_assessment()

    assert record["incrementality_status"] == "established"
    assert record["incrementality_evidence_scope"] == "simulation"


def test_simulation_keeps_real_world_decision_gaps():
    record = simulation_assessment()

    assert "real business outcomes" in record["decision_gaps"]
    assert "causal/incremental conversion" in record["decision_gaps"]


def test_simulation_claims_are_explicitly_synthetic():
    record = simulation_assessment()

    assert any(
        "synthetic simulation" in claim.lower()
        for claim in record["simulated_claims"]
    )
    assert any(
        "synthetic experiment" in claim.lower()
        for claim in record["simulated_claims"]
    )


def test_simulation_unknown_claims_keep_real_world_gaps():
    record = simulation_assessment()

    joined = " ".join(record["unknown_claims"]).lower()
    assert "real-world business outcomes not observed" in joined
    assert "production incremental" in joined


def test_simulation_assessment_uses_no_production_wording():
    record = simulation_assessment()

    for claim in record["simulated_claims"]:
        assert "production" not in claim.lower()
        assert "realized" not in claim.lower()
