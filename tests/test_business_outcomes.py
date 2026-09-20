import pytest

from foundry_prompt_agent.business_outcomes import (
    build_business_outcome_record,
    build_business_outcome_records,
)


def execution_record(interaction_id="alpha", accepted=True) -> dict:
    return {
        "run_id": "run1",
        "workload_id": "contoso-demand-recovery",
        "interaction_id": interaction_id,
        "accepted": accepted,
    }


def outcome_event(interaction_id="alpha", **overrides) -> dict:
    event = {"interaction_id": interaction_id}
    event.update(overrides)
    return event


def test_no_outcome_event_leaves_downstream_fields_none():
    record = build_business_outcome_record(execution_record(accepted=True))

    assert record["accepted"] is True
    for field in (
        "customer_engaged_after_response",
        "order_completed",
        "order_id",
        "order_value_usd",
        "incremental_order",
        "counterfactual_method",
        "outcome_evidence_source",
        "outcome_observed_at_utc",
    ):
        assert record[field] is None


def test_accepted_work_does_not_imply_order_completion():
    record = build_business_outcome_record(execution_record(accepted=True))

    # Accepted Work is an AI-quality signal, not a downstream outcome.
    assert record["order_completed"] is None


def test_observed_order_does_not_imply_incrementality():
    event = outcome_event(
        order_completed=True,
        order_id="ORD-1",
        order_value_usd=12.5,
        outcome_evidence_source="pos_system",
    )

    record = build_business_outcome_record(execution_record(), event)

    assert record["order_completed"] is True
    assert record["incremental_order"] is None
    assert record["counterfactual_method"] is None


def test_valid_observed_order_preserves_id_value_and_provenance():
    event = outcome_event(
        customer_engaged_after_response=True,
        order_completed=True,
        order_id="ORD-42",
        order_value_usd=9.75,
        outcome_evidence_source="pos_system",
        outcome_observed_at_utc="2026-09-20T10:00:00+00:00",
    )

    record = build_business_outcome_record(execution_record(), event)

    assert record["order_id"] == "ORD-42"
    assert record["order_value_usd"] == 9.75
    assert record["outcome_evidence_source"] == "pos_system"
    assert record["outcome_observed_at_utc"] == "2026-09-20T10:00:00+00:00"


def test_negative_order_value_is_rejected():
    event = outcome_event(order_completed=True, order_value_usd=-1.0)

    with pytest.raises(ValueError):
        build_business_outcome_record(execution_record(), event)


def test_incrementality_claim_requires_counterfactual_method():
    event = outcome_event(order_completed=True, incremental_order=True)

    with pytest.raises(ValueError):
        build_business_outcome_record(execution_record(), event)


def test_incrementality_with_counterfactual_is_preserved():
    event = outcome_event(
        order_completed=True,
        incremental_order=True,
        counterfactual_method="holdout_group",
    )

    record = build_business_outcome_record(execution_record(), event)

    assert record["incremental_order"] is True
    assert record["counterfactual_method"] == "holdout_group"


def test_mismatched_interaction_identity_fails_loudly():
    event = outcome_event(interaction_id="beta", order_completed=True)

    with pytest.raises(ValueError):
        build_business_outcome_record(execution_record("alpha"), event)


def test_batch_join_uses_interaction_id_not_ordering():
    records = [
        execution_record("alpha"),
        execution_record("beta"),
    ]
    events = [
        outcome_event("beta", order_completed=True, order_id="B"),
        outcome_event("alpha", order_completed=True, order_id="A"),
    ]

    joined = build_business_outcome_records(records, events)
    by_id = {r["interaction_id"]: r for r in joined}

    assert by_id["alpha"]["order_id"] == "A"
    assert by_id["beta"]["order_id"] == "B"


def test_batch_rejects_duplicate_outcome_event_ids():
    records = [execution_record("alpha")]
    events = [
        outcome_event("alpha", order_id="A1"),
        outcome_event("alpha", order_id="A2"),
    ]

    with pytest.raises(ValueError):
        build_business_outcome_records(records, events)


def test_batch_missing_event_stays_unknown():
    records = [execution_record("alpha"), execution_record("beta")]
    events = [outcome_event("alpha", order_completed=True)]

    joined = build_business_outcome_records(records, events)
    by_id = {r["interaction_id"]: r for r in joined}

    assert by_id["alpha"]["order_completed"] is True
    assert by_id["beta"]["order_completed"] is None


def test_batch_event_without_matching_record_fails_loudly():
    records = [execution_record("alpha")]
    events = [outcome_event("ghost", order_completed=True)]

    with pytest.raises(ValueError):
        build_business_outcome_records(records, events)


def test_batch_without_events_persists_all_unknown():
    records = [execution_record("alpha"), execution_record("beta")]

    joined = build_business_outcome_records(records, outcome_events=None)

    assert all(r["order_completed"] is None for r in joined)
    assert all(r["outcome_evidence_source"] is None for r in joined)
