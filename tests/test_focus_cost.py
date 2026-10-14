from datetime import date
import importlib.util
from pathlib import Path

import pytest

from foundry_prompt_agent.azure_runtime_cost import (
    build_azure_runtime_cost_config,
    load_azure_runtime_allocation_config,
    summarize_azure_runtime_cost,
)
from foundry_prompt_agent.cost_snapshot import (
    build_cost_snapshot,
    load_cost_snapshot,
    save_cost_snapshot,
    validate_cost_snapshot,
)
from foundry_prompt_agent.focus_cost import (
    load_focus_cost_data,
    month_period,
    normalize_focus_resource_costs,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "economics" / "azure_runtime_cost.yaml"
FIXTURE_PATH = ROOT / "focus_samples" / "contoso-september-2026.csv"
START = date(2026, 9, 1)
END = date(2026, 9, 30)
TODAY = date(2026, 10, 13)


@pytest.fixture
def config():
    return load_azure_runtime_allocation_config(CONFIG_PATH)


@pytest.fixture
def rows():
    return load_focus_cost_data(FIXTURE_PATH)


def normalize(rows, config, **kwargs):
    return normalize_focus_resource_costs(
        rows=rows,
        allocation_config=config,
        start=START,
        end=END,
        today=TODAY,
        **kwargs,
    )


def summary(rows, config, **kwargs):
    evidence = normalize(rows, config, **kwargs)
    attached = build_azure_runtime_cost_config(
        allocation_config=config,
        cost_evidence=evidence,
    )
    return summarize_azure_runtime_cost(attached)


def test_loads_fixture_and_default_metric_is_effective_cost(config, rows):
    evidence = normalize(rows, config)

    assert len(rows) == 6
    assert evidence["source"] == {
        "type": "focus_cost_and_usage",
        "focus_version": "1.2",
        "cost_metric": "effective_cost",
        "cost_basis": "effective_cost",
        "evidence_status": "observed_billing",
    }
    assert evidence["resources"][0]["actual_cost_usd"] == pytest.approx(241.92)


def test_csv_requires_selected_metric_and_contract_columns(tmp_path):
    path = tmp_path / "missing.csv"
    path.write_text(
        "ResourceId,BillingPeriodStart,BillingPeriodEnd,EffectiveCost\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="BillingCurrency"):
        load_focus_cost_data(path)


def test_invalid_numeric_cost_rejected(config, rows):
    rows[0]["EffectiveCost"] = "not-a-number"
    with pytest.raises(ValueError, match="EffectiveCost"):
        normalize(rows, config)


def test_mixed_currency_rejected(config, rows):
    rows[1]["BillingCurrency"] = "EUR"
    with pytest.raises(ValueError, match="only USD"):
        normalize(rows, config)


def test_rows_outside_requested_month_are_filtered(config, rows):
    rows.append(
        {
            **rows[0],
            "BillingPeriodStart": "2026-10-01",
            "BillingPeriodEnd": "2026-10-31",
            "EffectiveCost": "9999.00",
        }
    )
    result = summary(rows, config)
    assert result["actual_selected_resource_cost_usd"] == pytest.approx(
        246.061882
    )


def test_overlapping_partial_period_is_rejected(config, rows):
    rows[0]["BillingPeriodEnd"] = "2026-09-15"
    with pytest.raises(ValueError, match="complete billing period"):
        normalize(rows, config)


def test_multiple_rows_aggregate_and_resource_ids_match_case_insensitively(
    config, rows
):
    rows[0]["ResourceId"] = rows[0]["ResourceId"].lower()
    evidence = normalize(rows, config)
    search = evidence["resources"][0]

    assert search["actual_cost_usd"] == pytest.approx(241.92)
    assert search["cost_evidence_status"] == "observed_billing"


def test_signed_cost_rows_aggregate_before_nonnegative_contract_validation(
    config, rows
):
    rows.append(
        {
            **rows[0],
            "EffectiveCost": "-1.00",
            "BilledCost": "-1.00",
        }
    )
    result = summary(rows, config)
    assert result["resource_allocations"][0]["actual_cost_usd"] == pytest.approx(
        240.92
    )


def test_negative_aggregated_resource_cost_is_rejected(config, rows):
    rows.clear()
    rows.append(
        {
            "ResourceId": config["resources"][0]["resource_id"],
            "BillingCurrency": "USD",
            "BillingPeriodStart": "2026-09-01",
            "BillingPeriodEnd": "2026-09-30",
            "EffectiveCost": "-1.00",
        }
    )
    with pytest.raises(ValueError, match="aggregated FOCUS cost must be nonnegative"):
        normalize(rows, config)


def test_null_and_non_allow_list_resource_ids_are_ignored(config, rows):
    rows.extend(
        [
            {
                **rows[0],
                "ResourceId": None,
                "EffectiveCost": "1000000",
                "BillingCurrency": "EUR",
            },
            {
                **rows[0],
                "ResourceId": "/subscriptions/not-allowed/resource",
                "EffectiveCost": "1000000",
                "BillingCurrency": "EUR",
            },
        ]
    )
    result = summary(rows, config)
    assert result["actual_selected_resource_cost_usd"] == pytest.approx(
        246.061882
    )


def test_billed_cost_is_an_explicit_distinct_basis(config, rows):
    rows[0]["BilledCost"] = "130.00"
    evidence = normalize(rows, config, cost_metric="billed_cost")
    result = summarize_azure_runtime_cost(
        build_azure_runtime_cost_config(
            allocation_config=config,
            cost_evidence=evidence,
        )
    )

    assert evidence["source"]["cost_metric"] == "billed_cost"
    assert evidence["source"]["cost_basis"] == "billed_cost"
    assert result["actual_selected_resource_cost_usd"] == pytest.approx(
        256.061882
    )


@pytest.mark.parametrize("metric", ["actual_cost", "EffectiveCost", "", None])
def test_unsupported_cost_metric_rejected(metric):
    with pytest.raises(ValueError, match="cost_metric"):
        normalize_focus_resource_costs(
            rows=[],
            allocation_config={"resources": []},
            start=START,
            end=END,
            cost_metric=metric,
            today=TODAY,
        )


def test_direct_resource_absence_stays_missing_and_blocks_allocation(config, rows):
    search_id = config["resources"][0]["resource_id"].casefold()
    rows = [
        row for row in rows if row["ResourceId"].casefold() != search_id
    ]
    evidence = normalize(rows, config)
    search = evidence["resources"][0]
    assert search["actual_cost_usd"] is None
    assert search["cost_evidence_status"] == "not_returned"

    with pytest.raises(ValueError, match="missing billing evidence.*not_returned"):
        summary(rows, config)


def test_optional_absent_resource_is_no_direct_charge_not_observed_zero(config, rows):
    evidence = normalize(rows, config)
    app_insights = evidence["resources"][3]

    assert app_insights["actual_cost_usd"] == 0
    assert app_insights["cost_evidence_status"] == "no_direct_charge_returned"
    result = summary(rows, config)
    assert result["resource_allocations"][3]["cost_evidence_status"] == (
        "no_direct_charge_returned"
    )


def test_month_period_parser():
    assert month_period("2026-09") == (START, END)
    for value in ("2026-9", "2026-13", "2026-09-01", "invalid"):
        with pytest.raises(ValueError):
            month_period(value)


def test_parity_with_azure_cost_management_style_evidence(config, rows):
    focus_result = summary(rows, config)
    api_evidence = {
        "period": {"start": "2026-09-01", "end": "2026-09-30", "currency": "USD"},
        "source": {
            "type": "azure_cost_management_api",
            "cost_basis": "actual_cost",
            "evidence_status": "observed_billing",
            "scope": "subscription",
        },
        "resources": [
            {
                "name": config["resources"][0]["name"],
                "resource_id": config["resources"][0]["resource_id"],
                "billing_expectation": "direct_charge_expected",
                "actual_cost_usd": 241.92,
                "cost_evidence_status": "observed_billing",
            },
            {
                "name": config["resources"][1]["name"],
                "resource_id": config["resources"][1]["resource_id"],
                "billing_expectation": "direct_charge_expected",
                "actual_cost_usd": 4.123483,
                "cost_evidence_status": "observed_billing",
            },
            {
                "name": config["resources"][2]["name"],
                "resource_id": config["resources"][2]["resource_id"],
                "billing_expectation": "direct_charge_expected",
                "actual_cost_usd": 0.018399,
                "cost_evidence_status": "observed_billing",
            },
            {
                "name": config["resources"][3]["name"],
                "resource_id": config["resources"][3]["resource_id"],
                "billing_expectation": "may_be_billed_elsewhere",
                "actual_cost_usd": 0,
                "cost_evidence_status": "no_direct_charge_returned",
            },
        ],
    }
    api_result = summarize_azure_runtime_cost(
        build_azure_runtime_cost_config(
            allocation_config=config,
            cost_evidence=api_evidence,
        )
    )

    assert focus_result["actual_selected_resource_cost_usd"] == pytest.approx(
        api_result["actual_selected_resource_cost_usd"]
    )
    assert focus_result["allocated_azure_runtime_cost_usd"] == pytest.approx(
        api_result["allocated_azure_runtime_cost_usd"]
    )
    assert focus_result["actual_selected_resource_cost_usd"] == pytest.approx(
        246.061882
    )
    assert focus_result["allocated_azure_runtime_cost_usd"] == pytest.approx(
        52.525882
    )


def test_focus_snapshot_validates_and_loads_in_dashboard_snapshot_discovery(
    config, rows, tmp_path
):
    result = summary(rows, config)
    snapshot = build_cost_snapshot(
        azure_runtime_cost=result,
        snapshot_id="contoso-demand-recovery-focus-2026-09",
    )
    validate_cost_snapshot(snapshot)
    path = tmp_path / f"{snapshot['snapshot_id']}.json"
    save_cost_snapshot(snapshot, path)
    assert load_cost_snapshot(path, workload_id=config["workload_id"]) == snapshot

    spec = importlib.util.spec_from_file_location(
        "token_to_value_dashboard",
        ROOT / "apps" / "dashboard.py",
    )
    assert spec is not None and spec.loader is not None
    dashboard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dashboard)
    available, errors = dashboard.load_available_cost_snapshots(tmp_path)

    assert errors == []
    assert snapshot["snapshot_id"] in available
    assert available[snapshot["snapshot_id"]][1]["evidence_source"]["type"] == (
        "focus_cost_and_usage"
    )
