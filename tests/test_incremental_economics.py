import pytest

from foundry_prompt_agent.incremental_economics import (
    ECONOMICS_STATUS_ESTABLISHED,
    ECONOMICS_STATUS_NOT_ESTABLISHED,
    build_incremental_economics_record,
)


def build(increment=None, decision_id=None) -> dict:
    return build_incremental_economics_record(
        workload_id="contoso-demand-recovery",
        decision_id=decision_id,
        increment=increment,
    )


def full_increment(**overrides) -> dict:
    increment = {
        "increment_description": "additional 1,000 eligible interactions/month",
        "value_economic_basis_id": "expansion-2027Q1",
        "incremental_value_usd": 500.0,
        "incremental_value_evidence_status": "incremental_value_established",
        "incremental_customer_cost_usd": 120.0,
        "incremental_cost_completeness": "complete",
        "cost_economic_basis_id": "expansion-2027Q1",
    }
    increment.update(overrides)
    return increment


def test_no_increment_leaves_everything_unknown():
    record = build(increment=None)

    assert record["increment_description"] is None
    assert record["economic_basis_id"] is None
    assert record["incremental_value_usd"] is None
    assert record["incremental_customer_cost_usd"] is None
    assert record["incremental_net_economic_value_usd"] is None
    assert record["economics_status"] == ECONOMICS_STATUS_NOT_ESTABLISHED


def test_increment_without_value_or_cost_has_no_delta_nev():
    increment = {
        "increment_description": "rollout to 10 stores",
        "value_economic_basis_id": "expansion-2027Q1",
    }

    record = build(increment=increment)

    assert record["incremental_net_economic_value_usd"] is None
    assert record["economics_status"] == ECONOMICS_STATUS_NOT_ESTABLISHED


def test_value_only_has_no_delta_nev():
    increment = full_increment(
        incremental_customer_cost_usd=None,
        incremental_cost_completeness=None,
    )

    record = build(increment=increment)

    assert record["incremental_value_usd"] == 500.0
    assert record["incremental_net_economic_value_usd"] is None


def test_cost_only_has_no_delta_nev():
    increment = full_increment(incremental_value_usd=None)

    record = build(increment=increment)

    assert record["incremental_customer_cost_usd"] == 120.0
    assert record["incremental_net_economic_value_usd"] is None


def test_complete_matching_basis_produces_delta_nev():
    record = build(increment=full_increment())

    assert record["incremental_net_economic_value_usd"] == pytest.approx(380.0)
    assert record["economics_status"] == ECONOMICS_STATUS_ESTABLISHED


def test_negative_delta_nev_preserved():
    record = build(
        increment=full_increment(
            incremental_value_usd=100.0, incremental_customer_cost_usd=250.0
        )
    )

    assert record["incremental_net_economic_value_usd"] == pytest.approx(-150.0)


def test_zero_delta_nev_preserved():
    record = build(
        increment=full_increment(
            incremental_value_usd=120.0, incremental_customer_cost_usd=120.0
        )
    )

    assert record["incremental_net_economic_value_usd"] == pytest.approx(0.0)


def test_zero_incremental_value_preserved_as_zero():
    record = build(increment=full_increment(incremental_value_usd=0.0))

    assert record["incremental_value_usd"] == 0.0
    assert record["incremental_net_economic_value_usd"] == pytest.approx(-120.0)


def test_zero_incremental_cost_preserved_as_zero():
    record = build(increment=full_increment(incremental_customer_cost_usd=0.0))

    assert record["incremental_customer_cost_usd"] == 0.0
    assert record["incremental_net_economic_value_usd"] == pytest.approx(500.0)


def test_mismatched_economic_basis_prevents_delta_nev():
    record = build(
        increment=full_increment(cost_economic_basis_id="expansion-2028Q1")
    )

    assert record["incremental_net_economic_value_usd"] is None
    assert record["economics_status"] == ECONOMICS_STATUS_NOT_ESTABLISHED


def test_partial_incremental_cost_prevents_delta_nev():
    record = build(
        increment=full_increment(incremental_cost_completeness="partial")
    )

    assert record["incremental_net_economic_value_usd"] is None


def test_modeled_history_cannot_leak_into_incremental_value():
    # Modeled contribution is not passed in and must never populate the record.
    record = build(increment=None)

    assert record["incremental_value_usd"] is None
    assert record["incremental_value_evidence_status"] is None
