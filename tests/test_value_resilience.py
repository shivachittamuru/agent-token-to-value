import json

import pytest

from foundry_prompt_agent.business_economics import scenario_from_measured_run
from foundry_prompt_agent.value_resilience import (
    RESILIENCE_NOT_CLASSIFIED,
    RESILIENCE_SCOPE,
    build_value_resilience_record,
)


def measured_run() -> dict:
    return {"success_rate": 1.0, "cost_per_task": 0.0078}


def assumptions(**overrides) -> dict:
    base = {
        "missed_contacts_per_day": 100,
        "ai_eligible_rate": 0.60,
        "conversion_rate": 0.30,
        "average_order_value_usd": 10.0,
        "contribution_margin": 0.35,
        "days_per_month": 30,
    }
    base.update(overrides)
    return base


def stress_spec() -> dict:
    return {
        "conversion_rate": [0.15, 0.0],
        "average_order_value_usd": [8.0],
        "contribution_margin": [0.28],
        "cost_stress_multiplier": [5.0, 10.0],
        "combined": [
            {"name": "downturn", "conversion_rate": 0.15, "cost_stress_multiplier": 5.0},
        ],
    }


def build(**overrides) -> dict:
    kwargs = {
        "workload_id": "contoso-demand-recovery",
        "measured_run": measured_run(),
        "assumptions": assumptions(),
        "stress_spec": stress_spec(),
    }
    kwargs.update(overrides)
    return build_value_resilience_record(**kwargs)


def scenario_by_name(record: dict, name: str) -> dict:
    return next(s for s in record["stress_scenarios"] if s["scenario"] == name)


def test_scope_remains_modeled_scenario():
    record = build()

    assert record["resilience_scope"] == RESILIENCE_SCOPE
    assert record["value_evidence_status"] == "modeled_only"


def test_base_case_preserved():
    record = build()
    expected = scenario_from_measured_run(measured_run(), assumptions())

    assert record["base_case"][
        "modeled_recovered_contribution_usd"
    ] == pytest.approx(expected["recovered_contribution_per_month"])
    assert record["base_case"][
        "modeled_ai_value_multiple"
    ] == pytest.approx(expected["ai_value_multiple"])


def test_conversion_stress_changes_modeled_economics():
    record = build()
    base = record["base_case"]["modeled_recovered_contribution_usd"]
    stressed = scenario_by_name(record, "conversion_rate=0.15")

    assert stressed["modeled_recovered_contribution_usd"] < base


def test_cost_stress_changes_modeled_economics():
    record = build()
    base = record["base_case"]["modeled_ai_value_multiple"]
    stressed = scenario_by_name(record, "cost_stress_multiplier=10.0")

    assert stressed["modeled_ai_value_multiple"] < base


def test_combined_stress_changes_multiple_inputs():
    record = build()
    combined = scenario_by_name(record, "downturn")

    assert set(combined["changed_inputs"]) == {
        "conversion_rate",
        "cost_stress_multiplier",
    }


def test_scenario_assumptions_preserved():
    record = build()
    stressed = scenario_by_name(record, "average_order_value_usd=8.0")

    assert stressed["assumptions"]["average_order_value_usd"] == 8.0
    # Untouched assumptions remain at their base values.
    assert stressed["assumptions"]["contribution_margin"] == 0.35


def test_break_even_conversion_preserved():
    record = build()
    expected = scenario_from_measured_run(measured_run(), assumptions())

    assert record["base_case"][
        "break_even_conversion_rate"
    ] == pytest.approx(expected["break_even_conversion_rate"])


def test_no_automatic_resilience_classification():
    record = build()

    assert record["resilience_status"] == RESILIENCE_NOT_CLASSIFIED


def test_structural_unknowns_remain_explicit():
    record = build()

    assert "real incremental conversion not established" in record[
        "structural_unknowns"
    ]
    assert "total relevant customer cost incomplete" in record[
        "structural_unknowns"
    ]
    assert len(record["structural_unknowns"]) >= 5


def test_zero_values_remain_zero_not_unknown():
    record = build()
    zero_conversion = scenario_by_name(record, "conversion_rate=0.0")

    assert zero_conversion["modeled_recovered_contribution_usd"] == 0.0


def test_no_probability_field_is_generated():
    record = build()
    serialized = json.dumps(record).lower()

    assert "probability" not in serialized
    assert "prob_" not in serialized


def test_no_stress_spec_yields_base_only():
    record = build(stress_spec=None)

    assert record["stress_scenarios"] == []
    assert record["base_case"]["scenario"] == "base"
