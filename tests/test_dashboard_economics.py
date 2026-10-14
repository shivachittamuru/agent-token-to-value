import ast
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "cost_snapshots" / "contoso-demand-recovery-2026-09.json"
SPEC = importlib.util.spec_from_file_location(
    "dashboard_under_test", ROOT / "apps" / "dashboard.py"
)
assert SPEC is not None and SPEC.loader is not None
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)


def test_snapshot_discovery_loads_local_workload_snapshot_and_reports_invalid_files(
    tmp_path,
):
    (tmp_path / "valid.json").write_bytes(SNAPSHOT_PATH.read_bytes())
    other_workload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    other_workload["workload_id"] = "another-workload"
    (tmp_path / "other-workload.json").write_text(
        json.dumps(other_workload), encoding="utf-8"
    )
    (tmp_path / "invalid.json").write_text("{invalid", encoding="utf-8")

    snapshots, errors = dashboard.load_available_cost_snapshots(tmp_path)

    assert list(snapshots) == ["contoso-demand-recovery-2026-09"]
    assert snapshots["contoso-demand-recovery-2026-09"][1][
        "allocated_azure_runtime_cost_usd"
    ] == pytest.approx(52.52588160724)
    assert len(errors) == 2
    assert any("workload_id does not match" in error for error in errors)
    assert any("invalid.json" in error for error in errors)


def test_snapshot_discovery_excludes_duplicate_ids(tmp_path):
    (tmp_path / "a.json").write_bytes(SNAPSHOT_PATH.read_bytes())
    (tmp_path / "b.json").write_bytes(SNAPSHOT_PATH.read_bytes())
    (tmp_path / "c.json").write_bytes(SNAPSHOT_PATH.read_bytes())

    snapshots, errors = dashboard.load_available_cost_snapshots(tmp_path)

    assert snapshots == {}
    assert len(errors) == 2
    assert all("duplicate snapshot_id" in error for error in errors)


def test_runtime_cost_chart_keeps_inference_and_azure_boundaries_separate():
    figure = dashboard.contribution_vs_cost_chart(
        {
            "recovered_contribution_per_month": 1701.0,
            "ai_inference_cost_per_month": 11.07324,
        },
        {"allocated_azure_runtime_cost_usd": 52.52588160724},
    )

    assert list(figure.data[0].x) == [
        "Recovered contribution",
        "Azure runtime cost",
        "AI inference cost",
    ]
    assert list(figure.data[0].y) == pytest.approx(
        [1701.0, 52.52588160724, 11.07324]
    )


def test_sensitivity_chart_keeps_runtime_and_inference_multiples_distinct(
    monkeypatch,
):
    scenarios = [
        {"recovered_contribution_per_month": 500 + index, "ai_value_multiple": 153.6}
        for index in range(51)
    ]

    def fake_conversion_sensitivity(
        measured, controls, conversion_rates, *, cost_stress_multiplier
    ):
        assert measured == {"run_id": "measured"}
        assert controls["days_per_month"] == 30
        assert len(conversion_rates) == 51
        assert cost_stress_multiplier == 1.0
        return scenarios

    monkeypatch.setattr(
        dashboard,
        "conversion_sensitivity",
        fake_conversion_sensitivity,
    )
    snapshot = {
        "workload_id": "contoso-demand-recovery",
        "period_days": 30,
        "allocated_azure_runtime_cost_usd": 50.0,
        "cost_period": {
            "start": "2026-09-01",
            "end": "2026-09-30",
            "currency": "USD",
        },
        "evidence_source": {
            "type": "azure_cost_management_api",
            "cost_basis": "actual_cost",
            "evidence_status": "observed_billing",
        },
        "allocation_status": "partially_allocated",
    }

    figure = dashboard.conversion_sensitivity_chart(
        {"run_id": "measured"},
        {"conversion_rate": 0.2, "cost_stress_multiplier": 1.0, "days_per_month": 30},
        snapshot,
    )

    assert [trace.name for trace in figure.data] == [
        "Azure Runtime Value Multiple",
        "AI Value Multiple - inference only",
    ]
    assert list(figure.data[0].y) == pytest.approx(
        [(500 + index) / 50 for index in range(51)]
    )
    assert list(figure.data[1].y) == [153.6] * 51


def test_dashboard_does_not_import_azure_ingestion():
    module_path = Path(dashboard.__file__)
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")

    assert not any(
        name.startswith(("azure.", "foundry_prompt_agent.azure_cost_management"))
        for name in imported
    )
