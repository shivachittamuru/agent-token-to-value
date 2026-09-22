import json

import pytest

from foundry_prompt_agent.synthetic_economics import (
    build_synthetic_economics_record,
)


def experiment_summary(
    treatment_conversion=0.25,
    control_conversion=0.10,
    treatment_count=16,
    control_count=4,
) -> dict:
    return {
        "eligible_interactions": treatment_count + control_count,
        "treatment_count": treatment_count,
        "control_count": control_count,
        "treatment_orders": round(treatment_conversion * treatment_count),
        "control_orders": round(control_conversion * control_count),
        "treatment_conversion": treatment_conversion,
        "control_conversion": control_conversion,
        "simulated_conversion_lift_pp": (
            (treatment_conversion - control_conversion) * 100
        ),
        "evidence": "synthetic_simulation",
    }


def outcome_events() -> list[dict]:
    return [
        {"interaction_id": "a", "order_completed": True, "order_value_usd": 8.0},
        {"interaction_id": "b", "order_completed": True, "order_value_usd": 12.0},
        {"interaction_id": "c", "order_completed": False, "order_value_usd": None},
    ]


def build(**kwargs) -> dict:
    params = {
        "experiment_summary": experiment_summary(),
        "outcome_events": outcome_events(),
        "contribution_margin": 0.35,
        "economic_basis_id": "synthetic-run1",
    }
    params.update(kwargs)
    return build_synthetic_economics_record(**params)


def test_incremental_conversion_uses_treatment_control_lift():
    record = build()

    assert record["simulated_incremental_conversion_rate"] == pytest.approx(0.15)


def test_sample_level_incremental_orders_uses_treatment_denominator():
    record = build()

    # (0.25 - 0.10) * 16 treatment interactions
    assert record[
        "simulated_incremental_orders_for_observed_sample"
    ] == pytest.approx(2.4)


def test_average_order_value_is_pooled_observed_synthetic():
    record = build()

    # Pooled over the two completed synthetic orders: (8 + 12) / 2.
    assert record["average_order_value_usd"] == pytest.approx(10.0)
    assert record["order_value_basis"] == "pooled_observed_synthetic_average_order_value"


def test_revenue_and_contribution_use_pooled_value_and_margin():
    record = build()

    assert record["simulated_incremental_revenue_usd"] == pytest.approx(24.0)
    assert record["simulated_incremental_contribution_usd"] == pytest.approx(8.4)


def test_carries_basis_and_provenance():
    record = build()

    assert record["economic_basis_id"] == "synthetic-run1"
    assert record["evidence_mode"] == "synthetic_simulation"
    assert record["counterfactual_method"] == "randomized_synthetic_control"


def test_no_production_or_realized_wording():
    serialized = json.dumps(build()).lower()

    for label in ("production", "realized", "real_customer", "crm"):
        assert label not in serialized


def test_no_orders_yields_zero_average_value():
    record = build(
        outcome_events=[
            {"interaction_id": "x", "order_completed": False, "order_value_usd": None}
        ]
    )

    assert record["average_order_value_usd"] == 0.0
    assert record["simulated_incremental_revenue_usd"] == 0.0
