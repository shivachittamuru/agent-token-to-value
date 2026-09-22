"""Population-level synthetic economics for the workload simulator.

Translates the synthetic randomized experiment into transparent, simulation-only
economic metrics. Everything here is explicitly synthetic: it demonstrates how
treatment/control evidence would flow through the framework and must never be
treated as production-established value. The causal claim exists only at the
population/experiment level; individual orders are never marked incremental.
"""

from __future__ import annotations

EVIDENCE_MODE = "synthetic_simulation"
COUNTERFACTUAL_METHOD = "randomized_synthetic_control"
ORDER_VALUE_BASIS = "pooled_observed_synthetic_average_order_value"


def _pooled_average_order_value(outcome_events: list[dict]) -> float:
    values = [
        event["order_value_usd"]
        for event in outcome_events
        if event.get("order_completed") and event.get("order_value_usd") is not None
    ]
    return sum(values) / len(values) if values else 0.0


def build_synthetic_economics_record(
    *,
    experiment_summary: dict,
    outcome_events: list[dict],
    contribution_margin: float,
    economic_basis_id: str,
) -> dict:
    """Build a simulation-only population value record from the experiment.

    Incremental orders are attributed at the population level via the
    treatment/control conversion lift times the treatment population; revenue
    and contribution use a pooled observed synthetic order-value basis.
    """

    treatment_conversion = experiment_summary["treatment_conversion"]
    control_conversion = experiment_summary["control_conversion"]
    treatment_count = experiment_summary["treatment_count"]

    incremental_conversion_rate = treatment_conversion - control_conversion
    incremental_orders = incremental_conversion_rate * treatment_count

    average_order_value_usd = _pooled_average_order_value(outcome_events)
    incremental_revenue_usd = incremental_orders * average_order_value_usd
    incremental_contribution_usd = incremental_revenue_usd * contribution_margin

    return {
        "economic_basis_id": economic_basis_id,
        "evidence_mode": EVIDENCE_MODE,
        "counterfactual_method": COUNTERFACTUAL_METHOD,
        "treatment_count": treatment_count,
        "control_count": experiment_summary["control_count"],
        "simulated_incremental_conversion_rate": incremental_conversion_rate,
        "simulated_incremental_orders_for_observed_sample": incremental_orders,
        "order_value_basis": ORDER_VALUE_BASIS,
        "average_order_value_usd": average_order_value_usd,
        "contribution_margin": contribution_margin,
        "simulated_incremental_revenue_usd": incremental_revenue_usd,
        "simulated_incremental_contribution_usd": incremental_contribution_usd,
    }
