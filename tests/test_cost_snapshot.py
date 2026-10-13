from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

import pytest

from foundry_prompt_agent.azure_runtime_cost import (
    build_azure_runtime_cost_config,
    load_azure_runtime_allocation_config,
    load_azure_runtime_cost_config,
    summarize_azure_runtime_cost,
)
from foundry_prompt_agent.cost_snapshot import (
    build_cost_snapshot,
    load_cost_snapshot,
    save_cost_snapshot,
    validate_cost_snapshot,
)

CONFIG_PATH = Path(__file__).resolve().parents[1] / "economics" / "azure_runtime_cost.yaml"


@pytest.fixture
def runtime_summary():
    return summarize_azure_runtime_cost(load_azure_runtime_cost_config(CONFIG_PATH))


@pytest.fixture
def snapshot(runtime_summary):
    return build_cost_snapshot(azure_runtime_cost=runtime_summary)


def test_valid_summary_builds_deterministic_period_snapshot(runtime_summary):
    before = deepcopy(runtime_summary)
    first = build_cost_snapshot(azure_runtime_cost=runtime_summary)
    second = build_cost_snapshot(azure_runtime_cost=runtime_summary)
    assert first["snapshot_id"] == second["snapshot_id"] == "contoso-demand-recovery-2026-09"
    assert first["workload_id"] == "contoso-demand-recovery"
    assert first["cost_period"] == runtime_summary["cost_period"]
    assert datetime.fromisoformat(first["created_at"]).tzinfo is not None
    assert first["evidence_source"] == runtime_summary["cost_source"]
    assert first["actual_selected_resource_cost_usd"] == pytest.approx(246.06)
    assert first["allocated_azure_runtime_cost_usd"] == pytest.approx(52.524)
    assert first["allocated_azure_runtime_cost_per_day_usd"] == pytest.approx(52.524 / 30)
    assert first["allocation_status"] == "partially_allocated"
    assert runtime_summary == before
    first["resource_allocations"][0]["actual_cost_usd"] = 0
    first["evidence_source"]["scope"] = "changed"
    assert runtime_summary == before


def test_custom_snapshot_id(runtime_summary):
    assert build_cost_snapshot(
        azure_runtime_cost=runtime_summary, snapshot_id="manual-september-v1"
    )["snapshot_id"] == "manual-september-v1"


def test_resource_provenance_preserved(runtime_summary, snapshot):
    for original, saved in zip(
        runtime_summary["resource_allocations"], snapshot["resource_allocations"], strict=True
    ):
        assert all(saved[field] == value for field, value in original.items())
        assert saved["cost_evidence_status"] == "observed_billing"
    search = snapshot["resource_allocations"][0]
    assert search["billing_expectation"] == "direct_charge_expected"
    assert search["allocation_percentage"] == 0.2
    assert search["allocated_cost_usd"] == pytest.approx(48.384)
    assert search["allocation_basis"] == "engineering_estimate"
    assert search["allocation_confidence"] == "approximate"


def test_live_style_snapshot_preserves_query_absence():
    config = load_azure_runtime_allocation_config(CONFIG_PATH)
    evidence = {
        "period": {"start": "2026-09-01", "end": "2026-09-30", "currency": "USD"},
        "source": {
            "type": "azure_cost_management_api", "cost_basis": "actual_cost",
            "evidence_status": "observed_billing", "scope": f"/subscriptions/{config['subscription_id']}",
        },
        "resources": [
            {"name": resource["name"], "actual_cost_usd": cost, "cost_evidence_status": "observed_billing"}
            for resource, cost in zip(config["resources"][:3], [241.92, 4.123483, 0.018399], strict=True)
        ],
    }
    summary = summarize_azure_runtime_cost(build_azure_runtime_cost_config(
        allocation_config=config, cost_evidence=evidence
    ))
    snapshot = build_cost_snapshot(azure_runtime_cost=summary)
    assert snapshot["actual_selected_resource_cost_usd"] == pytest.approx(246.061882)
    assert snapshot["allocated_azure_runtime_cost_usd"] == pytest.approx(52.525882)
    assert snapshot["evidence_source"] == evidence["source"]
    appinsights = snapshot["resource_allocations"][3]
    assert appinsights["billing_expectation"] == "may_be_billed_elsewhere"
    assert appinsights["cost_evidence_status"] == "no_direct_charge_returned"
    assert appinsights["actual_cost_usd"] == 0


def test_save_load_round_trip(snapshot, tmp_path):
    before = deepcopy(snapshot)
    path = tmp_path / "cost_snapshots" / f"{snapshot['snapshot_id']}.json"
    save_cost_snapshot(snapshot, path)
    assert load_cost_snapshot(path, workload_id=snapshot["workload_id"]) == snapshot
    assert snapshot == before
    assert list(path.parent.iterdir()) == [path]


def test_load_rejects_wrong_workload(snapshot, tmp_path):
    path = tmp_path / "snapshot.json"
    save_cost_snapshot(snapshot, path)
    with pytest.raises(ValueError, match="workload_id"):
        load_cost_snapshot(path, workload_id="different-workload")


@pytest.mark.parametrize("field", [
    "snapshot_id", "workload_id", "created_at", "cost_period", "period_days",
    "evidence_source", "actual_selected_resource_cost_usd", "allocated_azure_runtime_cost_usd",
    "allocated_azure_runtime_cost_per_day_usd", "allocation_status", "resource_allocations",
])
def test_missing_snapshot_fields_rejected(snapshot, field):
    del snapshot[field]
    with pytest.raises(ValueError, match=field):
        validate_cost_snapshot(snapshot)


@pytest.mark.parametrize(("field", "value"), [
    ("snapshot_id", ""), ("snapshot_id", "../unsafe"),
    ("created_at", "invalid"), ("created_at", "2026-10-01T00:00:00"),
    ("created_at", "2026-09-15T00:00:00+00:00"),
    ("workload_id", ""), ("period_days", True), ("period_days", 12),
    ("allocation_status", "exact"), ("resource_allocations", []),
    ("actual_selected_resource_cost_usd", -1),
    ("allocated_azure_runtime_cost_usd", 0),
    ("allocated_azure_runtime_cost_usd", float("nan")),
    ("allocated_azure_runtime_cost_per_day_usd", float("inf")),
])
def test_invalid_snapshot_values_rejected(snapshot, field, value):
    snapshot[field] = value
    with pytest.raises(ValueError):
        validate_cost_snapshot(snapshot)


@pytest.mark.parametrize(("field", "value"), [
    ("end", "2026-09-15"), ("start", "2026-09-02"),
    ("currency", "EUR"), ("start", "20260901"),
])
def test_invalid_snapshot_period(snapshot, field, value):
    snapshot["cost_period"][field] = value
    with pytest.raises(ValueError):
        validate_cost_snapshot(snapshot)


@pytest.mark.parametrize(("field", "value"), [
    ("allocated_cost_usd", 0), ("actual_cost_usd", -1),
    ("allocation_percentage", 1.1), ("cost_evidence_status", "not_returned"),
    ("billing_expectation", "unknown"),
])
def test_invalid_resource_evidence(snapshot, field, value):
    snapshot["resource_allocations"][0][field] = value
    with pytest.raises(ValueError):
        validate_cost_snapshot(snapshot)


def test_duplicate_resources_rejected(snapshot):
    snapshot["resource_allocations"].append(deepcopy(snapshot["resource_allocations"][0]))
    with pytest.raises(ValueError, match="duplicate resource name"):
        validate_cost_snapshot(snapshot)


def test_api_summary_cannot_default_missing_resource_status(runtime_summary):
    runtime_summary["cost_source"]["type"] = "azure_cost_management_api"
    with pytest.raises(ValueError, match="requires cost_evidence_status"):
        build_cost_snapshot(azure_runtime_cost=runtime_summary)


def test_invalid_snapshot_does_not_overwrite_existing(snapshot, tmp_path):
    path = tmp_path / "snapshot.json"
    save_cost_snapshot(snapshot, path)
    before = path.read_bytes()
    snapshot["allocated_azure_runtime_cost_usd"] = 999
    with pytest.raises(ValueError):
        save_cost_snapshot(snapshot, path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("text", ["not json", '{"snapshot_id":"one","snapshot_id":"two"}', "[]"])
def test_invalid_json_rejected(tmp_path, text):
    path = tmp_path / "invalid.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_cost_snapshot(path)


def test_serialization_failure_does_not_leave_partial_file(snapshot, tmp_path, monkeypatch):
    import foundry_prompt_agent.cost_snapshot as module

    def fail(*args, **kwargs):
        raise OSError("disk failure")

    monkeypatch.setattr(module.json, "dump", fail)
    path = tmp_path / "snapshot.json"
    with pytest.raises(OSError, match="disk failure"):
        save_cost_snapshot(snapshot, path)
    assert not list(tmp_path.iterdir())


def test_snapshot_import_is_azure_sdk_free():
    result = subprocess.run(
        [sys.executable, "-c", (
            "import sys; import foundry_prompt_agent.cost_snapshot; "
            "assert not any(name == 'azure' or name.startswith('azure.') for name in sys.modules)"
        )],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
