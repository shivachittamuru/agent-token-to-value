from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest

from foundry_prompt_agent.azure_runtime_cost import (
    apply_azure_runtime_cost_to_modeled_economics,
    load_azure_runtime_cost_config,
    summarize_azure_runtime_cost,
)
from foundry_prompt_agent.business_economics import (
    load_business_assumptions,
    scenario_from_measured_run,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "economics" / "azure_runtime_cost.yaml"


@pytest.fixture
def config():
    return load_azure_runtime_cost_config(CONFIG_PATH)


@pytest.fixture
def business():
    assumptions = load_business_assumptions(
        ROOT / "economics" / "business_assumptions.yaml"
    )
    return scenario_from_measured_run(
        {"success_rate": 0.90, "cost_per_task": 0.0074}, assumptions
    )


def test_loads_valid_september_config(config):
    assert config["workload_id"] == "contoso-demand-recovery"
    assert config["period"]["start"] == date(2026, 9, 1)
    assert config["source"]["evidence_status"] == "observed_billing"
    assert len(config["resources"]) == 4


def test_september_summary(config):
    summary = summarize_azure_runtime_cost(config)
    assert summary["actual_selected_resource_cost_usd"] == pytest.approx(246.06)
    assert summary["allocated_azure_runtime_cost_usd"] == pytest.approx(52.524)
    assert summary["period_days"] == 30
    assert summary["allocated_azure_runtime_cost_per_day_usd"] == pytest.approx(
        52.524 / 30
    )
    assert summary["allocation_status"] == "partially_allocated"
    assert summary["cost_source"] == config["source"]
    assert summary["cost_period"] == {
        "start": "2026-09-01", "end": "2026-09-30", "currency": "USD"
    }
    search = summary["resource_allocations"][0]
    assert search["allocated_cost_usd"] == pytest.approx(48.384)
    assert search["allocation_percentage"] == 0.20
    assert search["allocation_method"] == "fixed_percentage"
    assert search["allocation_basis"] == "engineering_estimate"
    assert search["allocation_confidence"] == "approximate"
    assert "shared across workloads" in search["allocation_reason"]
    assert "Log Analytics" in summary["resource_allocations"][3]["note"]


def test_direct_resources_allocate_one_hundred_percent(config):
    for resource in summarize_azure_runtime_cost(config)["resource_allocations"][1:]:
        assert resource["allocation_percentage"] == 1.0
        assert resource["allocated_cost_usd"] == resource["actual_cost_usd"]


@pytest.mark.parametrize("percentage", [0, 0.20, 1])
def test_fixed_percentage_accepts_inclusive_bounds(config, percentage):
    config["resources"][0]["allocation"]["percentage"] = percentage
    result = summarize_azure_runtime_cost(config)
    assert result["resource_allocations"][0]["allocated_cost_usd"] == pytest.approx(
        241.92 * percentage
    )


@pytest.mark.parametrize("percentage", [-0.01, 1.01, float("nan"), float("inf"), True, "0.2"])
def test_invalid_percentage_fails(config, percentage):
    config["resources"][0]["allocation"]["percentage"] = percentage
    with pytest.raises(ValueError, match="percentage"):
        summarize_azure_runtime_cost(config)


def test_direct_percentage_must_be_one(config):
    config["resources"][1]["allocation"]["percentage"] = 0.5
    with pytest.raises(ValueError, match="direct allocation requires percentage 1.0"):
        summarize_azure_runtime_cost(config)


@pytest.mark.parametrize("cost", [-1, float("nan"), float("inf"), True, "4.12"])
def test_invalid_actual_cost_fails(config, cost):
    config["resources"][0]["actual_cost_usd"] = cost
    with pytest.raises(ValueError, match="actual_cost_usd"):
        summarize_azure_runtime_cost(config)


def test_duplicate_resource_fails(config):
    config["resources"].append(deepcopy(config["resources"][0]))
    with pytest.raises(ValueError, match="duplicate resource name"):
        summarize_azure_runtime_cost(config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("end", "2026-08-31"),
        ("start", "not-a-date"),
        ("end", "2026-09-31"),
        ("start", "20260901"),
        ("currency", ""),
        ("currency", "EUR"),
    ],
)
def test_invalid_period_fails(config, field, value):
    config["period"][field] = value
    with pytest.raises(ValueError, match="period"):
        summarize_azure_runtime_cost(config)


def test_same_day_period_is_inclusive(config):
    config["period"]["start"] = "2026-09-30"
    result = summarize_azure_runtime_cost(config)
    assert result["period_days"] == 1
    assert result["allocated_azure_runtime_cost_per_day_usd"] == pytest.approx(52.524)


def test_unsupported_method_fails(config):
    config["resources"][0]["allocation"]["method"] = "query_share"
    with pytest.raises(ValueError, match="method is unsupported"):
        summarize_azure_runtime_cost(config)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("config", "workload_id"), ("config", "resources"),
        ("config", "period"), ("config", "source"),
        ("period", "start"), ("period", "end"), ("period", "currency"),
        ("source", "type"), ("source", "cost_basis"), ("source", "evidence_status"),
        ("resource", "name"), ("resource", "service"),
        ("resource", "billing_expectation"),
        ("resource", "actual_cost_usd"), ("resource", "allocation"),
        ("allocation", "method"), ("allocation", "percentage"),
        ("allocation", "basis"), ("allocation", "confidence"),
    ],
)
def test_missing_required_field_fails(config, section, field):
    sections = {
        "config": config,
        "period": config["period"],
        "source": config["source"],
        "resource": config["resources"][0],
        "allocation": config["resources"][0]["allocation"],
    }
    del sections[section][field]
    with pytest.raises(ValueError, match=f"missing required field: {field}"):
        summarize_azure_runtime_cost(config)


@pytest.mark.parametrize("invalid", [None, [], {}, {"resources": []}])
def test_invalid_config_fails(invalid):
    with pytest.raises(ValueError):
        summarize_azure_runtime_cost(invalid)


def test_load_validates_contract(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text("workload_id: contoso-demand-recovery\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required field: resources"):
        load_azure_runtime_cost_config(path)


@pytest.mark.parametrize("expectation", ["unknown", "", None])
def test_invalid_billing_expectation_fails(config, expectation):
    config["resources"][0]["billing_expectation"] = expectation
    with pytest.raises(ValueError, match="billing_expectation"):
        summarize_azure_runtime_cost(config)


@pytest.mark.parametrize(
    ("index", "cost"),
    [(0, 0), (3, 1), (3, True)],
)
def test_no_direct_charge_status_cannot_bypass_evidence_validation(config, index, cost):
    resource = config["resources"][index]
    resource["cost_evidence_status"] = "no_direct_charge_returned"
    resource["actual_cost_usd"] = cost
    with pytest.raises(ValueError):
        summarize_azure_runtime_cost(config)


def test_direct_only_status_preserves_observed_billing(config):
    config["resources"] = config["resources"][1:]
    result = summarize_azure_runtime_cost(config)
    assert result["allocation_status"] == "directly_allocated"
    assert result["cost_source"]["evidence_status"] == "observed_billing"


def test_runtime_adjusted_economics_are_a_separate_lens(config, business):
    runtime = summarize_azure_runtime_cost(config)
    before_business = deepcopy(business)
    before_runtime = deepcopy(runtime)
    result = apply_azure_runtime_cost_to_modeled_economics(
        modeled_business_economics=business, azure_runtime_cost=runtime
    )
    assert result["modeled_recovered_contribution_usd"] == pytest.approx(1701)
    assert result["allocated_azure_runtime_cost_usd"] == pytest.approx(52.524)
    assert result["modeled_contribution_after_azure_runtime_usd"] == pytest.approx(
        1701 - 52.524
    )
    assert result["modeled_azure_runtime_value_multiple"] == pytest.approx(
        1701 / 52.524
    )
    assert result["cost_period"] == runtime["cost_period"]
    assert result["cost_source"] == runtime["cost_source"]
    assert result["allocation_status"] == "partially_allocated"
    assert business == before_business
    assert runtime == before_runtime
    assert business["ai_value_multiple"] == pytest.approx(1701 / 13.32)
    assert set(result) == {
        "modeled_recovered_contribution_usd",
        "allocated_azure_runtime_cost_usd",
        "modeled_contribution_after_azure_runtime_usd",
        "modeled_azure_runtime_value_multiple",
        "cost_period", "cost_source", "allocation_status",
    }
    result["cost_source"]["evidence_status"] = "changed"
    result["cost_period"]["start"] = "changed"
    assert runtime == before_runtime


@pytest.mark.parametrize("contribution", [0, 1701])
def test_zero_runtime_cost_is_safe(config, contribution):
    for resource in config["resources"]:
        resource["actual_cost_usd"] = 0
    result = apply_azure_runtime_cost_to_modeled_economics(
        modeled_business_economics={"recovered_contribution_per_month": contribution},
        azure_runtime_cost=summarize_azure_runtime_cost(config),
    )
    assert result["modeled_azure_runtime_value_multiple"] == float("inf")
    assert result["modeled_contribution_after_azure_runtime_usd"] == contribution


def test_runtime_cost_does_not_promote_customer_cost_or_incremental_claims(config, business):
    business["total_relevant_customer_cost_usd"] = None
    business["customer_cost_completeness"] = "partial"
    business["incremental_contribution_usd"] = None
    before = deepcopy(business)
    result = apply_azure_runtime_cost_to_modeled_economics(
        modeled_business_economics=business,
        azure_runtime_cost=summarize_azure_runtime_cost(config),
    )
    assert business == before
    for forbidden in (
        "roi", "realized", "customer_net_economic_value",
        "total_relevant_customer_cost", "customer_cost_completeness", "incremental",
    ):
        assert not any(forbidden in key.lower() for key in result)


def test_contribution_can_be_less_than_runtime_cost(config):
    result = apply_azure_runtime_cost_to_modeled_economics(
        modeled_business_economics={"recovered_contribution_per_month": 10},
        azure_runtime_cost=summarize_azure_runtime_cost(config),
    )
    assert result["modeled_contribution_after_azure_runtime_usd"] == pytest.approx(-42.524)


@pytest.mark.parametrize("field", ["recovered_contribution_per_month", "allocated_azure_runtime_cost_usd"])
def test_runtime_economics_rejects_invalid_amounts(config, business, field):
    runtime = summarize_azure_runtime_cost(config)
    target = business if field == "recovered_contribution_per_month" else runtime
    target[field] = float("nan")
    with pytest.raises(ValueError, match=field):
        apply_azure_runtime_cost_to_modeled_economics(
            modeled_business_economics=business, azure_runtime_cost=runtime
        )
