"""Seeded synthetic business experiment for the Contoso workload simulator.

Layers a *simulated* pilot (randomized treatment/control assignment and
synthetic customer outcomes) on top of REAL agent execution and REAL technical
evaluation. Everything produced here is explicitly synthetic and must never be
represented as production observation or production causal evidence.

Key modeling rules:
- Assignment is randomized and precedes outcome generation.
- Assignment never depends on Accepted Work.
- Control outcomes depend only on the configured baseline (no AI dependence).
- Treatment outcomes may depend on Accepted Work (a post-treatment mediator).
- Failed treatment interactions remain in the treatment denominator.
- Individual orders are never marked incremental; only the population-level
  synthetic comparison carries (simulated) causal meaning.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

OUTCOME_SIMULATOR_VERSION = "1"

EVIDENCE_SOURCE = "synthetic_simulation"
COUNTERFACTUAL_METHOD = "randomized_synthetic_control"
PILOT_ID = "synthetic-pilot-001"

# Exposure provenance: a real execution record must never imply the control
# customer received AI. Control agent execution is shadow-only measurement.
EXPOSURE_TREATMENT = "ai_exposed_to_simulated_customer"
EXPOSURE_CONTROL = "ai_not_exposed_shadow_execution_only"

# Transparent simulation assumptions. These are NOT claims about real Contoso
# behavior; they parameterize the synthetic experiment only.
DEFAULT_SIMULATION_CONFIG = {
    "control_conversion_rate": 0.12,
    "treatment_accepted_conversion_rate": 0.25,
    "treatment_rejected_conversion_rate": 0.06,
    "treatment_share": 0.5,
    "attribution_window_minutes": 60,
    "contribution_margin": 0.35,
    "min_order_value_usd": 3.0,
    "max_order_value_usd": 12.0,
}

_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _sub_rng(seed: int, purpose: str, interaction_id: str) -> random.Random:
    # Per-interaction, per-purpose seeding keeps results independent of
    # ordering and stable for the same seed + inputs.
    return random.Random(f"{seed}:{purpose}:{interaction_id}")


def simulate_pilot_outcomes(
    *,
    interaction_records: list[dict],
    seed: int,
    config: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    """Simulate pilot assignment and synthetic business outcomes.

    ``interaction_records`` need only carry ``interaction_id`` and ``accepted``
    (execution records after the Accepted Work join). Returns ``(pilot_events,
    business_outcome_events)`` keyed by ``interaction_id`` and compatible with
    ``build_pilot_evidence_records`` / ``build_business_outcome_records``.
    """

    cfg = {**DEFAULT_SIMULATION_CONFIG, **(config or {})}
    attribution_window = cfg["attribution_window_minutes"]

    pilot_events = []
    outcome_events = []

    for record in interaction_records:
        interaction_id = record["interaction_id"]
        accepted = record.get("accepted")

        # 1. Assignment first, independent of Accepted Work.
        assign_rng = _sub_rng(seed, "assign", interaction_id)
        is_treatment = assign_rng.random() < cfg["treatment_share"]
        assignment = "treatment" if is_treatment else "control"
        exposure = EXPOSURE_TREATMENT if is_treatment else EXPOSURE_CONTROL

        pilot_events.append(
            {
                "interaction_id": interaction_id,
                "pilot_id": PILOT_ID,
                "eligible": True,
                "assignment": assignment,
                "assigned_at_utc": _BASE_TIME.isoformat(),
                "staff_unavailable": True,
                "attribution_window_minutes": attribution_window,
                "protocol_deviation": None,
                "protocol_deviation_reason": None,
                # Synthetic provenance (ignored by the domain builder).
                "exposure": exposure,
                "evidence_mode": EVIDENCE_SOURCE,
                "simulated": True,
            }
        )

        # 2. Outcome after assignment.
        outcome_rng = _sub_rng(seed, "outcome", interaction_id)
        value_rng = _sub_rng(seed, "value", interaction_id)

        if is_treatment:
            probability = (
                cfg["treatment_accepted_conversion_rate"]
                if accepted is True
                else cfg["treatment_rejected_conversion_rate"]
            )
        else:
            # Control never depends on AI acceptance/response/quality.
            probability = cfg["control_conversion_rate"]

        order_completed = outcome_rng.random() < probability

        # Order value is independent of assignment (separate stream).
        order_value = round(
            value_rng.uniform(
                cfg["min_order_value_usd"], cfg["max_order_value_usd"]
            ),
            2,
        )
        observed_offset = outcome_rng.randint(1, attribution_window)
        observed_at = (
            _BASE_TIME + timedelta(minutes=observed_offset)
        ).isoformat()

        outcome_events.append(
            {
                "interaction_id": interaction_id,
                # For treatment, engagement is proxied by ordering; control has
                # no AI response, so post-response engagement is not applicable.
                "customer_engaged_after_response": (
                    order_completed if is_treatment else None
                ),
                "order_completed": order_completed,
                "order_id": f"sim-order-{interaction_id}" if order_completed else None,
                "order_value_usd": order_value if order_completed else None,
                # Never per-record incremental; only the population comparison
                # carries simulated causal meaning.
                "incremental_order": None,
                "counterfactual_method": COUNTERFACTUAL_METHOD,
                "outcome_evidence_source": EVIDENCE_SOURCE,
                "outcome_observed_at_utc": observed_at,
            }
        )

    return pilot_events, outcome_events


def summarize_experiment(
    pilot_events: list[dict],
    outcome_events: list[dict],
) -> dict:
    """Summarize the synthetic experiment. This is simulated, not realized."""

    orders_by_id = {
        event["interaction_id"]: bool(event["order_completed"])
        for event in outcome_events
    }

    eligible = sum(1 for event in pilot_events if event["eligible"] is True)
    treatment = [e for e in pilot_events if e["assignment"] == "treatment"]
    control = [e for e in pilot_events if e["assignment"] == "control"]

    treatment_orders = sum(
        1 for e in treatment if orders_by_id.get(e["interaction_id"])
    )
    control_orders = sum(
        1 for e in control if orders_by_id.get(e["interaction_id"])
    )

    treatment_conversion = (
        treatment_orders / len(treatment) if treatment else 0.0
    )
    control_conversion = control_orders / len(control) if control else 0.0

    return {
        "eligible_interactions": eligible,
        "treatment_count": len(treatment),
        "control_count": len(control),
        "treatment_orders": treatment_orders,
        "control_orders": control_orders,
        "treatment_conversion": treatment_conversion,
        "control_conversion": control_conversion,
        "simulated_conversion_lift_pp": (
            (treatment_conversion - control_conversion) * 100
        ),
        "evidence": EVIDENCE_SOURCE,
    }


def build_simulation_metadata(
    *,
    inquiry_seed: int,
    outcome_seed: int,
    count: int,
    generator_version: str,
    config: dict | None = None,
) -> dict:
    """Assemble run-level simulation metadata with independent seeds."""

    return {
        "inquiry_seed": inquiry_seed,
        "outcome_seed": outcome_seed,
        "count": count,
        "generator_version": generator_version,
        "outcome_simulator_version": OUTCOME_SIMULATOR_VERSION,
        "business_simulation_config": {
            **DEFAULT_SIMULATION_CONFIG,
            **(config or {}),
        },
    }
