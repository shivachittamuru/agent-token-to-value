"""Business Outcome Evidence records — the PROVE-phase evidence contract.

This module deliberately answers a different question than the rest of the
package:

- ``execution.py`` records what the AI system did.
- ``business_outcomes.py`` records what happened downstream in the
  workflow/business (customer engagement, orders, incrementality).
- ``business_economics.py`` models economics / valuation.

Downstream outcomes are never inferred from Accepted Work, model output,
evaluator results, tool usage, or business assumptions. When no downstream
evidence exists, the fields stay Unknown (None) rather than False or zero.
"""

from __future__ import annotations

DOWNSTREAM_FIELDS = (
    "customer_engaged_after_response",
    "order_completed",
    "order_id",
    "order_value_usd",
    "incremental_order",
    "counterfactual_method",
    "outcome_evidence_source",
    "outcome_observed_at_utc",
)


def build_business_outcome_record(
    execution_record: dict,
    outcome_event: dict | None = None,
) -> dict:
    """Build one Business Outcome Evidence record for an interaction.

    Without an ``outcome_event`` every downstream field remains None (Unknown).
    With one, fields are copied from observed evidence only; a completed order
    never implies incrementality, which requires an explicit counterfactual.
    """

    record = {
        "run_id": execution_record["run_id"],
        "workload_id": execution_record["workload_id"],
        "interaction_id": execution_record["interaction_id"],
        "accepted": execution_record.get("accepted"),
    }

    for field in DOWNSTREAM_FIELDS:
        record[field] = None

    if outcome_event is None:
        return record

    interaction_id = execution_record["interaction_id"]
    if outcome_event.get("interaction_id") != interaction_id:
        raise ValueError(
            "Outcome event interaction_id "
            f"{outcome_event.get('interaction_id')!r} does not match "
            f"execution record {interaction_id!r}"
        )

    order_value_usd = outcome_event.get("order_value_usd")
    if order_value_usd is not None and order_value_usd < 0:
        raise ValueError(
            f"Negative order_value_usd for {interaction_id!r}: {order_value_usd}"
        )

    incremental_order = outcome_event.get("incremental_order")
    counterfactual_method = outcome_event.get("counterfactual_method")
    if incremental_order is not None and counterfactual_method is None:
        # Incrementality is a claim; it cannot be invented from order presence.
        raise ValueError(
            "incremental_order requires counterfactual_method for "
            f"{interaction_id!r}"
        )

    for field in DOWNSTREAM_FIELDS:
        record[field] = outcome_event.get(field)

    return record


def build_business_outcome_records(
    execution_records: list[dict],
    outcome_events: list[dict] | None = None,
) -> list[dict]:
    """Join outcome events onto execution records by stable interaction id.

    Joins never rely on ordering. Duplicate outcome-event interaction ids and
    events that match no execution record both fail loudly. Records without a
    matching event keep every downstream field Unknown.
    """

    events_by_id: dict[str, dict] = {}
    for event in outcome_events or []:
        interaction_id = event.get("interaction_id")
        if interaction_id is None:
            raise ValueError("Outcome event is missing interaction_id")
        if interaction_id in events_by_id:
            raise ValueError(
                f"Duplicate outcome-event interaction_id: {interaction_id!r}"
            )
        events_by_id[interaction_id] = event

    execution_ids = {record["interaction_id"] for record in execution_records}
    for interaction_id in events_by_id:
        if interaction_id not in execution_ids:
            raise ValueError(
                "Outcome event has no matching execution record: "
                f"{interaction_id!r}"
            )

    return [
        build_business_outcome_record(
            record, events_by_id.get(record["interaction_id"])
        )
        for record in execution_records
    ]
