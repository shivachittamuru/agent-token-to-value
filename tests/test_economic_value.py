import pytest

from foundry_prompt_agent.economic_value import (
    VALUE_EVIDENCE_INCREMENTAL_ESTABLISHED,
    VALUE_EVIDENCE_MODELED_ONLY,
    build_economic_value_record,
)


def modeled(recovered_contribution=1890.0, ai_value_multiple=128.6, **extra) -> dict:
    base = {
        "recovered_contribution_per_month": recovered_contribution,
        "ai_value_multiple": ai_value_multiple,
        # Modeled recovered orders must never leak into incremental value.
        "recovered_orders_per_day": 18.0,
    }
    base.update(extra)
    return base


def execution_economics(cost_completeness="partial", known_direct=0.08) -> dict:
    return {
        "known_direct_execution_cost_usd": known_direct,
        "cost_completeness": cost_completeness,
    }


def build(**overrides) -> dict:
    kwargs = {
        "run_id": "run1",
        "workload_id": "contoso-demand-recovery",
        "modeled_business_economics": modeled(),
        "execution_economics": execution_economics(),
        "incremental_evidence": None,
    }
    kwargs.update(overrides)
    return build_economic_value_record(**kwargs)


def test_current_run_is_modeled_only():
    record = build()

    assert record["value_evidence_status"] == VALUE_EVIDENCE_MODELED_ONLY
    assert record["customer_net_economic_value_usd"] is None


def test_modeled_contribution_stays_modeled():
    record = build()

    assert record["modeled_recovered_contribution_usd"] == 1890.0
    assert record["modeled_ai_value_multiple"] == 128.6
    # Not relabelled as realized/incremental.
    assert "realized_contribution_usd" not in record
    assert record["incremental_contribution_usd"] is None


def test_no_incremental_evidence_keeps_incremental_fields_none():
    record = build(incremental_evidence=None)

    assert record["incremental_orders"] is None
    assert record["incremental_revenue_usd"] is None
    assert record["incremental_contribution_usd"] is None


def test_accepted_work_cannot_populate_incremental_value():
    # Modeled recovered orders exist, but incremental value must stay Unknown.
    record = build(modeled_business_economics=modeled(recovered_orders_per_day=18.0))

    assert record["incremental_orders"] is None
    assert record["incremental_contribution_usd"] is None


def test_partial_cost_keeps_customer_nev_none():
    record = build(
        execution_economics=execution_economics(cost_completeness="partial"),
        incremental_evidence={"incremental_contribution_usd": 100.0},
    )

    assert record["customer_net_economic_value_usd"] is None


def test_complete_execution_cost_alone_does_not_produce_nev():
    # Execution-cost completeness must not stand in for customer-cost completeness.
    record = build(
        execution_economics=execution_economics(cost_completeness="complete"),
        incremental_evidence={"incremental_contribution_usd": 17.5},
    )

    assert record["customer_net_economic_value_usd"] is None


def test_incremental_with_complete_execution_cost_but_no_customer_cost():
    record = build(
        execution_economics=execution_economics(cost_completeness="complete"),
        incremental_evidence={
            "incremental_orders": 5,
            "incremental_contribution_usd": 17.5,
            "value_economic_basis_id": "pilot-2026Q4",
        },
    )

    assert (
        record["value_evidence_status"]
        == VALUE_EVIDENCE_INCREMENTAL_ESTABLISHED
    )
    assert record["customer_net_economic_value_usd"] is None


def test_incremental_with_incomplete_customer_cost_still_no_nev():
    record = build(
        execution_economics=execution_economics(cost_completeness="complete"),
        incremental_evidence={
            "incremental_contribution_usd": 17.5,
            "value_economic_basis_id": "pilot-2026Q4",
            "total_relevant_customer_cost_usd": 4.0,
            "customer_cost_completeness": "partial",
            "cost_economic_basis_id": "pilot-2026Q4",
        },
    )

    assert record["customer_net_economic_value_usd"] is None


def test_complete_customer_cost_and_matching_basis_produces_nev():
    record = build(
        execution_economics=execution_economics(cost_completeness="partial"),
        incremental_evidence={
            "incremental_orders": 5,
            "incremental_revenue_usd": 50.0,
            "incremental_contribution_usd": 17.5,
            "value_economic_basis_id": "pilot-2026Q4",
            "total_relevant_customer_cost_usd": 4.0,
            "customer_cost_completeness": "complete",
            "cost_economic_basis_id": "pilot-2026Q4",
        },
    )

    # NEV uses the Total Relevant Customer Cost, never execution cost.
    assert record["customer_net_economic_value_usd"] == pytest.approx(13.5)


def test_mismatched_economic_basis_keeps_nev_none():
    record = build(
        execution_economics=execution_economics(cost_completeness="complete"),
        incremental_evidence={
            "incremental_contribution_usd": 17.5,
            "value_economic_basis_id": "pilot-2026Q4",
            "total_relevant_customer_cost_usd": 4.0,
            "customer_cost_completeness": "complete",
            "cost_economic_basis_id": "pilot-2027Q1",
        },
    )

    assert record["customer_net_economic_value_usd"] is None


def test_value_status_is_separate_from_cost_completeness():
    record = build(
        execution_economics=execution_economics(cost_completeness="partial"),
        incremental_evidence={"incremental_contribution_usd": 17.5},
    )

    assert (
        record["value_evidence_status"]
        == VALUE_EVIDENCE_INCREMENTAL_ESTABLISHED
    )
    assert record["cost_completeness"] == "partial"
    assert record["customer_cost_completeness"] is None


def test_zero_incremental_value_is_preserved_not_unknown():
    record = build(
        execution_economics=execution_economics(cost_completeness="partial"),
        incremental_evidence={
            "incremental_contribution_usd": 0.0,
            "value_economic_basis_id": "pilot-2026Q4",
            "total_relevant_customer_cost_usd": 4.0,
            "customer_cost_completeness": "complete",
            "cost_economic_basis_id": "pilot-2026Q4",
        },
    )

    assert record["incremental_contribution_usd"] == 0.0
    assert (
        record["value_evidence_status"]
        == VALUE_EVIDENCE_INCREMENTAL_ESTABLISHED
    )
    # NEV = 0 incremental value - Total Relevant Customer Cost.
    assert record["customer_net_economic_value_usd"] == pytest.approx(-4.0)
