"""Incremental Economics records — next-dollar decision economics.

This answers a different question than ``economic_value.py``: if we make an
explicit additional investment in the workload, what additional value and
additional cost would that proposed change create?

Incremental value is never inferred from modeled scenario economics, the
modeled AI Value Multiple, Accepted Work, or treatment outcomes without a
counterfactual. Incremental customer cost is never inferred from historical
run cost or average cost per interaction. A proposed increment must be
explicit, and value and cost must share one declared economic basis before
an incremental net economic value is computed.
"""

from __future__ import annotations

ECONOMICS_STATUS_NOT_ESTABLISHED = "not_established"
ECONOMICS_STATUS_ESTABLISHED = "incremental_net_value_established"


def build_incremental_economics_record(
    *,
    workload_id: str,
    decision_id: str | None = None,
    increment: dict | None = None,
) -> dict:
    """Build one run-level Incremental Economics record.

    Without an explicit ``increment`` every incremental field stays Unknown.
    Incremental Net Economic Value is computed only when the increment is
    defined and value and cost are both established, complete, and declared on
    the same economic basis.
    """

    increment_description = None
    economic_basis_id = None
    incremental_value_usd = None
    incremental_value_evidence_status = None
    incremental_customer_cost_usd = None
    incremental_cost_completeness = None
    cost_economic_basis_id = None

    if increment is not None:
        increment_description = increment.get("increment_description")
        economic_basis_id = increment.get("value_economic_basis_id")
        incremental_value_usd = increment.get("incremental_value_usd")
        incremental_value_evidence_status = increment.get(
            "incremental_value_evidence_status"
        )
        incremental_customer_cost_usd = increment.get(
            "incremental_customer_cost_usd"
        )
        incremental_cost_completeness = increment.get(
            "incremental_cost_completeness"
        )
        cost_economic_basis_id = increment.get("cost_economic_basis_id")

    basis_matches = (
        economic_basis_id is not None
        and economic_basis_id == cost_economic_basis_id
    )

    incremental_net_economic_value_usd = None
    if (
        increment_description is not None
        and incremental_value_usd is not None
        and incremental_customer_cost_usd is not None
        and incremental_cost_completeness == "complete"
        and basis_matches
    ):
        incremental_net_economic_value_usd = (
            incremental_value_usd - incremental_customer_cost_usd
        )

    economics_status = (
        ECONOMICS_STATUS_ESTABLISHED
        if incremental_net_economic_value_usd is not None
        else ECONOMICS_STATUS_NOT_ESTABLISHED
    )

    return {
        "decision_id": decision_id,
        "workload_id": workload_id,
        "increment_description": increment_description,
        "economic_basis_id": economic_basis_id,
        "incremental_value_usd": incremental_value_usd,
        "incremental_value_evidence_status": incremental_value_evidence_status,
        "incremental_customer_cost_usd": incremental_customer_cost_usd,
        "incremental_cost_completeness": incremental_cost_completeness,
        "incremental_net_economic_value_usd": incremental_net_economic_value_usd,
        "economics_status": economics_status,
    }
