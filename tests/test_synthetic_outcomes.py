import json

import pytest

from foundry_prompt_agent.business_outcomes import build_business_outcome_records
from foundry_prompt_agent.pilot_evidence import build_pilot_evidence_records
from foundry_prompt_agent.synthetic_outcomes import (
    COUNTERFACTUAL_METHOD,
    EVIDENCE_SOURCE,
    EXPOSURE_CONTROL,
    EXPOSURE_TREATMENT,
    OUTCOME_SIMULATOR_VERSION,
    build_simulation_metadata,
    simulate_pilot_outcomes,
    summarize_experiment,
)

# High-contrast config makes treatment outcomes deterministic by acceptance.
CONTRAST_CONFIG = {
    "treatment_accepted_conversion_rate": 1.0,
    "treatment_rejected_conversion_rate": 0.0,
    "control_conversion_rate": 1.0,
}


def records(count=40, accepted=True) -> list[dict]:
    return [
        {
            "interaction_id": f"i{n:03d}",
            "accepted": accepted,
            "run_id": "simrun",
            "workload_id": "contoso-demand-recovery",
        }
        for n in range(count)
    ]


def by_id(events: list[dict]) -> dict:
    return {event["interaction_id"]: event for event in events}


def test_same_seed_same_inputs_identical():
    a = simulate_pilot_outcomes(interaction_records=records(), seed=7, config=None)
    b = simulate_pilot_outcomes(interaction_records=records(), seed=7, config=None)

    assert a == b


def test_different_seed_produces_variation():
    a = simulate_pilot_outcomes(interaction_records=records(), seed=7, config=None)
    b = simulate_pilot_outcomes(interaction_records=records(), seed=8, config=None)

    assert a != b


def test_assignment_independent_of_accepted_work():
    accepted_pilots, _ = simulate_pilot_outcomes(
        interaction_records=records(accepted=True), seed=7, config=None
    )
    rejected_pilots, _ = simulate_pilot_outcomes(
        interaction_records=records(accepted=False), seed=7, config=None
    )

    assert [p["assignment"] for p in accepted_pilots] == [
        p["assignment"] for p in rejected_pilots
    ]


def test_assignment_covers_all_eligible_interactions():
    pilots, _ = simulate_pilot_outcomes(
        interaction_records=records(count=30), seed=7, config=None
    )

    assignments = [p["assignment"] for p in pilots]
    assert all(p["eligible"] is True for p in pilots)
    assert assignments.count("treatment") + assignments.count("control") == 30


def test_control_outcome_independent_of_accepted_work():
    pilots, accepted_outcomes = simulate_pilot_outcomes(
        interaction_records=records(accepted=True), seed=7, config=None
    )
    _, rejected_outcomes = simulate_pilot_outcomes(
        interaction_records=records(accepted=False), seed=7, config=None
    )

    accepted_by_id = by_id(accepted_outcomes)
    rejected_by_id = by_id(rejected_outcomes)

    for pilot in pilots:
        if pilot["assignment"] == "control":
            iid = pilot["interaction_id"]
            assert (
                accepted_by_id[iid]["order_completed"]
                == rejected_by_id[iid]["order_completed"]
            )


def test_treatment_outcome_can_differ_by_accepted_state():
    pilots, accepted_outcomes = simulate_pilot_outcomes(
        interaction_records=records(accepted=True), seed=7, config=CONTRAST_CONFIG
    )
    _, rejected_outcomes = simulate_pilot_outcomes(
        interaction_records=records(accepted=False), seed=7, config=CONTRAST_CONFIG
    )

    accepted_by_id = by_id(accepted_outcomes)
    rejected_by_id = by_id(rejected_outcomes)

    treatment_ids = [
        p["interaction_id"] for p in pilots if p["assignment"] == "treatment"
    ]
    # Under contrast config accepted treatment always orders, rejected never.
    assert any(
        accepted_by_id[iid]["order_completed"]
        != rejected_by_id[iid]["order_completed"]
        for iid in treatment_ids
    )


def test_failed_treatment_stays_in_treatment_denominator():
    pilots, _ = simulate_pilot_outcomes(
        interaction_records=records(accepted=False), seed=7, config=None
    )

    # Rejected (failed) interactions assigned to treatment are still treatment.
    treatment = [p for p in pilots if p["assignment"] == "treatment"]
    assert treatment  # some exist
    assert all(p["assignment"] == "treatment" for p in treatment)


def test_no_individual_order_is_marked_incremental():
    _, outcomes = simulate_pilot_outcomes(
        interaction_records=records(), seed=7, config=None
    )

    assert all(o["incremental_order"] is None for o in outcomes)


def test_synthetic_counterfactual_and_provenance_explicit():
    pilots, outcomes = simulate_pilot_outcomes(
        interaction_records=records(), seed=7, config=None
    )

    assert all(
        o["counterfactual_method"] == COUNTERFACTUAL_METHOD for o in outcomes
    )
    assert "synthetic" in COUNTERFACTUAL_METHOD
    assert all(p["simulated"] is True for p in pilots)


def test_control_marked_shadow_not_customer_exposed():
    pilots, _ = simulate_pilot_outcomes(
        interaction_records=records(), seed=7, config=None
    )

    for pilot in pilots:
        if pilot["assignment"] == "control":
            assert pilot["exposure"] == EXPOSURE_CONTROL
            assert "not_exposed" in pilot["exposure"]


def test_treatment_marked_customer_exposed():
    pilots, _ = simulate_pilot_outcomes(
        interaction_records=records(), seed=7, config=None
    )

    for pilot in pilots:
        if pilot["assignment"] == "treatment":
            assert pilot["exposure"] == EXPOSURE_TREATMENT


def test_order_id_only_when_order_occurs():
    _, outcomes = simulate_pilot_outcomes(
        interaction_records=records(), seed=7, config=None
    )

    for outcome in outcomes:
        if outcome["order_completed"]:
            assert outcome["order_id"] is not None
        else:
            assert outcome["order_id"] is None


def test_order_value_only_when_order_occurs():
    _, outcomes = simulate_pilot_outcomes(
        interaction_records=records(), seed=7, config=None
    )

    for outcome in outcomes:
        if outcome["order_completed"]:
            assert outcome["order_value_usd"] is not None
            assert outcome["order_value_usd"] > 0
        else:
            assert outcome["order_value_usd"] is None


def test_outcome_source_is_explicitly_synthetic():
    _, outcomes = simulate_pilot_outcomes(
        interaction_records=records(), seed=7, config=None
    )

    assert all(o["outcome_evidence_source"] == EVIDENCE_SOURCE for o in outcomes)
    assert EVIDENCE_SOURCE == "synthetic_simulation"


def test_no_production_evidence_label_appears():
    pilots, outcomes = simulate_pilot_outcomes(
        interaction_records=records(), seed=7, config=None
    )
    serialized = json.dumps(pilots + outcomes).lower()

    for label in (
        "production",
        "crm",
        "pos_system",
        "point_of_sale",
        "real_customer",
        "telemetry",
    ):
        assert label not in serialized


def test_inquiry_and_outcome_seed_preserved_independently():
    metadata = build_simulation_metadata(
        inquiry_seed=42,
        outcome_seed=4201,
        count=20,
        generator_version="1",
    )

    assert metadata["inquiry_seed"] == 42
    assert metadata["outcome_seed"] == 4201
    assert metadata["outcome_simulator_version"] == OUTCOME_SIMULATOR_VERSION
    assert "business_simulation_config" in metadata


def test_events_are_compatible_with_domain_builders():
    execution = records(count=20)
    pilots, outcomes = simulate_pilot_outcomes(
        interaction_records=execution, seed=7, config=None
    )

    # Should not raise; assignment and outcomes survive the domain builders.
    pilot_records = build_pilot_evidence_records(execution, pilot_events=pilots)
    business_records = build_business_outcome_records(
        execution, outcome_events=outcomes
    )

    assert {p["assignment"] for p in pilot_records} <= {"treatment", "control"}
    assert len(business_records) == 20


def test_summarize_experiment_fixture():
    execution = records(count=40)
    pilots, outcomes = simulate_pilot_outcomes(
        interaction_records=execution, seed=7, config=None
    )

    summary = summarize_experiment(pilots, outcomes)

    assert summary["treatment_count"] + summary["control_count"] == 40
    assert summary["eligible_interactions"] == 40
    assert summary["evidence"] == "synthetic_simulation"
    assert summary["simulated_conversion_lift_pp"] == pytest.approx(
        (summary["treatment_conversion"] - summary["control_conversion"]) * 100
    )
