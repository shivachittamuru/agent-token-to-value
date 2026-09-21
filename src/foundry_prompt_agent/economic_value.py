"""Economic Value records — the VALUE phase evidence contract.

This module separates value claims by how they are justified:

- *Modeled* value comes from the scenario model in ``business_economics.py``
  and stays modeled; it is never relabelled realized or incremental.
- *Incremental* value requires counterfactual (pilot) evidence and is never
  derived from assumptions, Accepted Work, or recovered-order projections.
- *Customer Net Economic Value* is only computed when defensible incremental
  value exists AND the relevant customer cost is complete.

Value evidence status and cost completeness are deliberately kept as two
separate fields, never combined into a single score.
"""

from __future__ import annotations

VALUE_EVIDENCE_MODELED_ONLY = "modeled_only"
VALUE_EVIDENCE_OBSERVED_NOT_INCREMENTAL = "observed_not_incremental"
VALUE_EVIDENCE_INCREMENTAL_ESTABLISHED = "incremental_value_established"


def build_economic_value_record(
    *,
    run_id: str,
    workload_id: str,
    modeled_business_economics: dict,
    execution_economics: dict,
    incremental_evidence: dict | None = None,
) -> dict:
    """Build one run-level Economic Value record.

    Preserves the modeled scenario result explicitly, carries incremental
    value only when backed by counterfactual evidence, and computes Customer
    Net Economic Value only when incremental value exists and cost is complete.
    """

    incremental_orders = None
    incremental_revenue_usd = None
    incremental_contribution_usd = None
    value_economic_basis_id = None
    total_relevant_customer_cost_usd = None
    customer_cost_completeness = None
    cost_economic_basis_id = None
    if incremental_evidence is not None:
        incremental_orders = incremental_evidence.get("incremental_orders")
        incremental_revenue_usd = incremental_evidence.get(
            "incremental_revenue_usd"
        )
        incremental_contribution_usd = incremental_evidence.get(
            "incremental_contribution_usd"
        )
        value_economic_basis_id = incremental_evidence.get(
            "value_economic_basis_id"
        )
        total_relevant_customer_cost_usd = incremental_evidence.get(
            "total_relevant_customer_cost_usd"
        )
        customer_cost_completeness = incremental_evidence.get(
            "customer_cost_completeness"
        )
        cost_economic_basis_id = incremental_evidence.get(
            "cost_economic_basis_id"
        )

    known_direct_execution_cost_usd = execution_economics[
        "known_direct_execution_cost_usd"
    ]
    cost_completeness = execution_economics["cost_completeness"]

    if incremental_contribution_usd is not None:
        value_evidence_status = VALUE_EVIDENCE_INCREMENTAL_ESTABLISHED
    elif incremental_evidence is not None:
        value_evidence_status = VALUE_EVIDENCE_OBSERVED_NOT_INCREMENTAL
    else:
        value_evidence_status = VALUE_EVIDENCE_MODELED_ONLY

    # Customer NEV requires established incremental value AND an explicit,
    # complete Total Relevant Customer Cost declared on the same economic
    # basis. Execution cost is evidence only; it is never used as the cost
    # term here, and execution-cost completeness does not imply customer-cost
    # completeness.
    basis_matches = (
        value_economic_basis_id is not None
        and value_economic_basis_id == cost_economic_basis_id
    )
    customer_net_economic_value_usd = None
    if (
        incremental_contribution_usd is not None
        and total_relevant_customer_cost_usd is not None
        and customer_cost_completeness == "complete"
        and basis_matches
    ):
        customer_net_economic_value_usd = (
            incremental_contribution_usd - total_relevant_customer_cost_usd
        )

    return {
        "run_id": run_id,
        "workload_id": workload_id,
        "value_evidence_status": value_evidence_status,
        "economic_basis_id": value_economic_basis_id,
        # Modeled scenario economics — remain modeled, never realized.
        "modeled_recovered_contribution_usd": modeled_business_economics[
            "recovered_contribution_per_month"
        ],
        "modeled_ai_value_multiple": modeled_business_economics[
            "ai_value_multiple"
        ],
        # Incremental attributable value — requires counterfactual evidence.
        "incremental_orders": incremental_orders,
        "incremental_revenue_usd": incremental_revenue_usd,
        "incremental_contribution_usd": incremental_contribution_usd,
        # Execution cost evidence — currently PARTIAL, not a full/customer cost.
        "known_direct_execution_cost_usd": known_direct_execution_cost_usd,
        "cost_completeness": cost_completeness,
        # Total Relevant Customer Cost — separate from execution cost.
        "total_relevant_customer_cost_usd": total_relevant_customer_cost_usd,
        "customer_cost_completeness": customer_cost_completeness,
        # Customer Net Economic Value — only with incremental value AND a
        # complete Total Relevant Customer Cost on a matching basis.
        "customer_net_economic_value_usd": customer_net_economic_value_usd,
    }
