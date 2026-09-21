import pytest

from foundry_prompt_agent.pilot_evidence import (
    build_pilot_evidence_record,
    build_pilot_evidence_records,
)


def execution_record(interaction_id="alpha") -> dict:
    return {
        "run_id": "run1",
        "workload_id": "contoso-demand-recovery",
        "interaction_id": interaction_id,
        "accepted": True,
    }


def pilot_event(interaction_id="alpha", **overrides) -> dict:
    event = {"interaction_id": interaction_id}
    event.update(overrides)
    return event


def test_no_event_leaves_pilot_fields_unknown():
    record = build_pilot_evidence_record("alpha")

    assert record["interaction_id"] == "alpha"
    for field in (
        "pilot_id",
        "eligible",
        "assignment",
        "assigned_at_utc",
        "staff_unavailable",
        "attribution_window_minutes",
        "protocol_deviation",
        "protocol_deviation_reason",
    ):
        assert record[field] is None


def test_valid_treatment_record():
    event = pilot_event(
        pilot_id="pilot-1",
        eligible=True,
        assignment="treatment",
        assigned_at_utc="2026-09-20T10:00:00+00:00",
        staff_unavailable=True,
        attribution_window_minutes=60,
    )

    record = build_pilot_evidence_record("alpha", event)

    assert record["assignment"] == "treatment"
    assert record["attribution_window_minutes"] == 60
    assert record["pilot_id"] == "pilot-1"


def test_valid_control_record():
    event = pilot_event(assignment="control", eligible=True)

    record = build_pilot_evidence_record("alpha", event)

    assert record["assignment"] == "control"
    assert record["eligible"] is True


def test_invalid_assignment_rejected():
    event = pilot_event(assignment="placebo")

    with pytest.raises(ValueError):
        build_pilot_evidence_record("alpha", event)


def test_non_positive_attribution_window_rejected():
    event = pilot_event(assignment="treatment", attribution_window_minutes=0)

    with pytest.raises(ValueError):
        build_pilot_evidence_record("alpha", event)


def test_protocol_deviation_requires_reason():
    event = pilot_event(assignment="treatment", protocol_deviation=True)

    with pytest.raises(ValueError):
        build_pilot_evidence_record("alpha", event)


def test_reason_without_deviation_rejected():
    event = pilot_event(
        assignment="treatment",
        protocol_deviation=False,
        protocol_deviation_reason="staff intervened",
    )

    with pytest.raises(ValueError):
        build_pilot_evidence_record("alpha", event)


def test_protocol_deviation_with_reason_is_preserved():
    event = pilot_event(
        assignment="treatment",
        protocol_deviation=True,
        protocol_deviation_reason="staff intervened",
    )

    record = build_pilot_evidence_record("alpha", event)

    assert record["protocol_deviation"] is True
    assert record["protocol_deviation_reason"] == "staff intervened"


def test_mismatched_interaction_identity_fails_loudly():
    event = pilot_event(interaction_id="beta", assignment="treatment")

    with pytest.raises(ValueError):
        build_pilot_evidence_record("alpha", event)


def test_batch_join_uses_interaction_id_not_ordering():
    records = [execution_record("alpha"), execution_record("beta")]
    events = [
        pilot_event("beta", assignment="control", pilot_id="B"),
        pilot_event("alpha", assignment="treatment", pilot_id="A"),
    ]

    joined = build_pilot_evidence_records(records, events)
    by_id = {r["interaction_id"]: r for r in joined}

    assert by_id["alpha"]["assignment"] == "treatment"
    assert by_id["beta"]["assignment"] == "control"


def test_batch_rejects_duplicate_pilot_ids():
    records = [execution_record("alpha")]
    events = [
        pilot_event("alpha", assignment="treatment"),
        pilot_event("alpha", assignment="control"),
    ]

    with pytest.raises(ValueError):
        build_pilot_evidence_records(records, events)


def test_batch_event_without_matching_record_fails_loudly():
    records = [execution_record("alpha")]
    events = [pilot_event("ghost", assignment="treatment")]

    with pytest.raises(ValueError):
        build_pilot_evidence_records(records, events)


def test_batch_missing_event_remains_unknown():
    records = [execution_record("alpha"), execution_record("beta")]
    events = [pilot_event("alpha", assignment="treatment")]

    joined = build_pilot_evidence_records(records, events)
    by_id = {r["interaction_id"]: r for r in joined}

    assert by_id["alpha"]["assignment"] == "treatment"
    assert by_id["beta"]["assignment"] is None


def test_batch_without_events_persists_all_unknown():
    records = [execution_record("alpha"), execution_record("beta")]

    joined = build_pilot_evidence_records(records, pilot_events=None)

    assert all(r["assignment"] is None for r in joined)
    assert all(r["pilot_id"] is None for r in joined)
