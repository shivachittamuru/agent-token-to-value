"""Pilot Evidence records — experiment context for causal interpretation.

This module answers yet another distinct question:

- ``execution.py`` records technical execution evidence.
- ``pilot_evidence.py`` records pilot / experiment context (eligibility,
  treatment/control assignment, attribution window, protocol deviations).
- ``business_outcomes.py`` records downstream workflow/business outcomes.
- ``business_economics.py`` translates evidence into economics.

Pilot metadata is never inferred from the regression dataset, Accepted Work,
model output, or business assumptions. Without a pilot event the fields stay
Unknown (None) rather than being fabricated.
"""

from __future__ import annotations

VALID_ASSIGNMENTS = ("treatment", "control")

PILOT_FIELDS = (
    "pilot_id",
    "eligible",
    "assignment",
    "assigned_at_utc",
    "staff_unavailable",
    "attribution_window_minutes",
    "protocol_deviation",
    "protocol_deviation_reason",
)


def build_pilot_evidence_record(
    interaction_id: str,
    pilot_event: dict | None = None,
) -> dict:
    """Build one Pilot Evidence record for an interaction.

    Without a ``pilot_event`` every pilot field except ``interaction_id``
    remains None (Unknown). With one, fields are copied from observed pilot
    evidence only, after validating assignment, attribution window, and
    protocol-deviation consistency.
    """

    record = {"pilot_id": None, "interaction_id": interaction_id}
    for field in PILOT_FIELDS:
        if field != "pilot_id":
            record[field] = None

    if pilot_event is None:
        return record

    event_interaction_id = pilot_event.get("interaction_id")
    if event_interaction_id is not None and event_interaction_id != interaction_id:
        raise ValueError(
            "Pilot event interaction_id "
            f"{event_interaction_id!r} does not match {interaction_id!r}"
        )

    assignment = pilot_event.get("assignment")
    if assignment is not None and assignment not in VALID_ASSIGNMENTS:
        raise ValueError(
            f"Invalid assignment for {interaction_id!r}: {assignment!r}"
        )

    attribution_window = pilot_event.get("attribution_window_minutes")
    if attribution_window is not None and attribution_window <= 0:
        raise ValueError(
            "attribution_window_minutes must be positive for "
            f"{interaction_id!r}: {attribution_window}"
        )

    protocol_deviation = pilot_event.get("protocol_deviation")
    protocol_deviation_reason = pilot_event.get("protocol_deviation_reason")
    if protocol_deviation is True and protocol_deviation_reason is None:
        raise ValueError(
            f"protocol_deviation requires a reason for {interaction_id!r}"
        )
    if protocol_deviation_reason is not None and protocol_deviation is not True:
        raise ValueError(
            "protocol_deviation_reason requires protocol_deviation=True for "
            f"{interaction_id!r}"
        )

    for field in PILOT_FIELDS:
        record[field] = pilot_event.get(field)

    return record


def build_pilot_evidence_records(
    execution_records: list[dict],
    pilot_events: list[dict] | None = None,
) -> list[dict]:
    """Join pilot events onto execution records by stable interaction id.

    Joins never rely on ordering. Duplicate pilot-event interaction ids and
    events that match no execution record both fail loudly. Interactions
    without a matching event keep every pilot field Unknown.
    """

    events_by_id: dict[str, dict] = {}
    for event in pilot_events or []:
        interaction_id = event.get("interaction_id")
        if interaction_id is None:
            raise ValueError("Pilot event is missing interaction_id")
        if interaction_id in events_by_id:
            raise ValueError(
                f"Duplicate pilot-event interaction_id: {interaction_id!r}"
            )
        events_by_id[interaction_id] = event

    execution_ids = {record["interaction_id"] for record in execution_records}
    for interaction_id in events_by_id:
        if interaction_id not in execution_ids:
            raise ValueError(
                "Pilot event has no matching execution record: "
                f"{interaction_id!r}"
            )

    return [
        build_pilot_evidence_record(
            record["interaction_id"], events_by_id.get(record["interaction_id"])
        )
        for record in execution_records
    ]
