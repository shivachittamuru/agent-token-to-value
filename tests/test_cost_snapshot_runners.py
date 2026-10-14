from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from foundry_prompt_agent import azure_cost_management
from foundry_prompt_agent.azure_runtime_cost import (
    load_azure_runtime_cost_config,
    summarize_azure_runtime_cost,
)
from foundry_prompt_agent.cost_snapshot import build_cost_snapshot, save_cost_snapshot
from foundry_prompt_agent.business_economics import (
    load_business_assumptions,
    summarize_business_economics,
)

ROOT = Path(__file__).resolve().parents[1]


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runners(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("runner must never retrieve live Azure billing evidence")

    monkeypatch.setattr(azure_cost_management, "DefaultAzureCredential", forbidden)
    monkeypatch.setattr(azure_cost_management.AzureCostManagementAdapter, "query", forbidden)
    monkeypatch.setattr(azure_cost_management, "fetch_azure_resource_costs", forbidden)
    agent = ModuleType("foundry_prompt_agent.agent")
    agent.ask_agent = forbidden
    agent.project_client = SimpleNamespace(get_openai_client=lambda: object())
    evaluator = ModuleType("foundry_prompt_agent.foundry_eval")
    evaluator.BEHAVIOR_CRITERION = "behavior"
    evaluator.collect_accepted_work = lambda *args, **kwargs: {
        "accepted_interactions": 1, "attempted_interactions": 1, "rows": []
    }
    evaluator.get_pass_rate = lambda *args, **kwargs: 0.9
    evaluator.enforce_quality_gate = lambda *args, **kwargs: None
    evaluator.run_cloud_evaluation = lambda *args, **kwargs: SimpleNamespace(
        status="completed", report_url="mock-report"
    )
    monkeypatch.setitem(sys.modules, agent.__name__, agent)
    monkeypatch.setitem(sys.modules, evaluator.__name__, evaluator)
    monkeypatch.setattr(sys, "path", list(sys.path))
    evaluation = load_script("snapshot_evaluation_runner", ROOT / "scripts" / "run_evaluation.py")
    monkeypatch.setitem(sys.modules, "run_evaluation", evaluation)
    simulation = load_script("snapshot_simulation_runner", ROOT / "scripts" / "run_simulation.py")

    evaluation._console_printers = {
        name: function for name, function in vars(evaluation).items()
        if name.startswith("print_")
    }
    # Exercise the actual shared package pipeline; mock unrelated domain evidence.
    outputs = {
        "summarize_effectiveness": {},
        "summarize_accepted_work": {},
        "attribute_costs": {},
        "summarize_execution_economics": {"cost_completeness": "partial"},
        "build_business_outcome_records": [],
        "build_pilot_evidence_records": [],
        "summarize_business_economics": {
            "recovered_contribution_per_month": 1701, "ai_value_multiple": 117.8
        },
        "build_economic_value_record": {
            "customer_net_economic_value_usd": None,
            "value_evidence_status": "modeled_only",
        },
        "build_incremental_economics_record": {},
        "build_value_resilience_record": {},
        "build_workload_assessment": {},
        "build_decision_gate_record": {},
        "build_portfolio_action_record": {"selected_action": "prove"},
        "build_interaction_records": [],
        "build_history_record": {},
    }
    for name, value in outputs.items():
        monkeypatch.setattr(evaluation, name, lambda *args, result=value, **kwargs: deepcopy(result))
    for name in vars(evaluation):
        if name.startswith("print_") and name != "print_azure_runtime_economics":
            monkeypatch.setattr(evaluation, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(evaluation, "apply_acceptance", lambda records, rows: records)
    monkeypatch.setattr(evaluation, "ASSUMPTIONS_PATH", ROOT / "economics" / "business_assumptions.yaml")
    monkeypatch.setattr(evaluation.history, "append_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(evaluation, "build_run_id", lambda: "snapshot-test-run")
    monkeypatch.setattr(simulation, "build_run_id", evaluation.build_run_id)
    execute = lambda *args: ({"tasks": 1, "cost_per_task": 0.0074}, [])
    monkeypatch.setattr(evaluation, "run_agent_over_cases", execute)
    monkeypatch.setattr(simulation, "run_agent_over_cases", execute)
    monkeypatch.setattr(evaluation, "load_dataset", lambda *args: [])
    monkeypatch.setattr(simulation, "load_menu", lambda *args: {})
    monkeypatch.setattr(simulation, "generate_inquiries", lambda **kwargs: [])
    monkeypatch.setattr(simulation, "simulate_pilot_outcomes", lambda **kwargs: (None, None))
    monkeypatch.setattr(simulation, "print_synthetic_header", lambda *args: None)
    monkeypatch.setenv("FOUNDRY_JUDGE_MODEL", "mock-judge")
    monkeypatch.chdir(tmp_path)
    return {"evaluation": evaluation, "simulation": simulation}


@pytest.fixture
def saved_snapshot(tmp_path):
    summary = summarize_azure_runtime_cost(load_azure_runtime_cost_config(
        ROOT / "economics" / "azure_runtime_cost.yaml"
    ))
    snapshot = build_cost_snapshot(azure_runtime_cost=summary)
    path = tmp_path / "cost_snapshots" / f"{snapshot['snapshot_id']}.json"
    save_cost_snapshot(snapshot, path)
    return path, snapshot


@pytest.mark.parametrize("runner_name", ["evaluation", "simulation"])
@pytest.mark.parametrize("include_snapshot", [False, True])
def test_runners_persist_optional_local_snapshot(
    runners, saved_snapshot, tmp_path, monkeypatch, runner_name, include_snapshot
):
    path, snapshot = saved_snapshot
    args = [runner_name]
    if include_snapshot:
        args.extend(["--cost-snapshot", str(path)])
    monkeypatch.setattr(sys, "argv", args)
    runners[runner_name].main()
    package = tmp_path / "runs" / "snapshot-test-run"
    summary = json.loads((package / "summary.json").read_text(encoding="utf-8"))
    assert (package / "interactions.jsonl").exists()
    assert summary["run_mode"] == ("regression" if runner_name == "evaluation" else "simulation")
    assert summary["modeled_business_economics"]["ai_value_multiple"] == 117.8
    assert summary["economic_value"]["customer_net_economic_value_usd"] is None
    if include_snapshot:
        assert summary["azure_runtime_cost"]["snapshot_id"] == snapshot["snapshot_id"]
        assert summary["azure_runtime_cost"]["snapshot_path"] == str(path)
        assert summary["azure_runtime_cost"]["allocated_azure_runtime_cost_usd"] == pytest.approx(52.524)
        assert summary["azure_runtime_modeled_economics"]["modeled_azure_runtime_value_multiple"] == pytest.approx(1701 / 52.524)
    else:
        assert "azure_runtime_cost" not in summary
        assert "azure_runtime_modeled_economics" not in summary


@pytest.fixture
def live_saved_snapshot(tmp_path):
    config = load_azure_runtime_cost_config(ROOT / "economics" / "azure_runtime_cost.yaml")
    config["source"]["type"] = "azure_cost_management_api"
    for index, amount in enumerate([241.92, 4.123483, 0.018399, 0]):
        config["resources"][index]["actual_cost_usd"] = amount
        config["resources"][index]["cost_evidence_status"] = (
            "no_direct_charge_returned" if index == 3 else "observed_billing"
        )
    snapshot = build_cost_snapshot(azure_runtime_cost=summarize_azure_runtime_cost(config))
    path = tmp_path / "live-september.json"
    save_cost_snapshot(snapshot, path)
    return path, snapshot


@pytest.mark.parametrize("runner_name", ["evaluation", "simulation"])
@pytest.mark.parametrize("compatible", [False, True])
def test_runtime_console_and_persistence_follow_basis(
    runners, live_saved_snapshot, tmp_path, monkeypatch, capsys, runner_name, compatible
):
    evaluation = runners["evaluation"]
    path, snapshot = live_saved_snapshot
    assumptions = load_business_assumptions(ROOT / "economics" / "business_assumptions.yaml")
    assumptions["days_per_month"] = 30 if compatible else 12
    business = summarize_business_economics(
        **assumptions, success_rate=0.9, cost_per_task_usd=0.0061518
    )
    monkeypatch.setattr(evaluation, "load_business_assumptions", lambda *args: assumptions)
    monkeypatch.setattr(evaluation, "summarize_business_economics", lambda **kwargs: business)
    execution = {
        "attempted_interactions": 10, "accepted_interactions": 9,
        "known_direct_execution_cost_usd": 0.061518,
        "known_direct_cost_per_attempt_usd": 0.0061518,
        "known_direct_cost_per_accepted_work_usd": 0.061518 / 9,
        "measured_tool_calls": 10, "cost_completeness": "partial",
        "unknown_or_unallocated_components": ["azure_ai_search", "observability", "human_recovery"],
    }
    monkeypatch.setattr(evaluation, "summarize_execution_economics", lambda *args: execution)
    for name in ("print_execution_economics", "print_business_economics"):
        monkeypatch.setattr(evaluation, name, evaluation._console_printers[name])
    monkeypatch.setattr(sys, "argv", [runner_name, "--cost-snapshot", str(path)])
    runners[runner_name].main()
    output = capsys.readouterr().out
    assert "Modeled AI Value Multiple: 153.6x" in output
    expected_inference_cost = "$11.07" if compatible else "$4.43"
    assert f"AI inference cost/month: {expected_inference_cost}" in output
    assert "Not attributed at run level:" in output
    assert "  - azure_ai_search" in output
    assert "  - observability" in output
    assert "  - human_recovery" in output
    assert "AVAILABLE VIA COST SNAPSHOT" in output
    assert "Full Execution Cost: NOT YET ESTABLISHED" in output
    summary = json.loads(
        (tmp_path / "runs" / "snapshot-test-run" / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["execution_economics"] == execution
    assert summary["modeled_business_economics"] == business
    assert summary["economic_value"]["customer_net_economic_value_usd"] is None
    assert summary["portfolio_action"]["selected_action"] == "prove"
    assert summary["azure_runtime_cost"]["cost_period"] == snapshot["cost_period"]
    if compatible:
        assert "=== Azure Runtime Economics ===" in output
        assert "Cost period: 2026-09-01 to 2026-09-30" in output
        assert "Actual selected Azure resource cost: $246.06" in output
        assert "Allocated Azure runtime cost: $52.53" in output
        assert "Allocation status: PARTIALLY ALLOCATED" in output
        assert "Modeled recovered contribution/month: $1,701.00" in output
        assert "Modeled contribution after Azure runtime: $1,648.47" in output
        assert "Modeled Azure Runtime Value Multiple: 32.4x" in output
        assert "Evidence boundary: PERIOD-LEVEL AZURE OPERATING COST" in output
        assert summary["azure_runtime_modeled_economics"]["modeled_azure_runtime_value_multiple"] == pytest.approx(1701 / 52.525882)
    else:
        assert "=== Azure Runtime Economics ===" not in output
        assert "monthly basis not established or incompatible" in output
        assert "azure_runtime_modeled_economics" not in summary


def test_no_snapshot_console_keeps_runtime_section_absent(runners, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["evaluation"])
    runners["evaluation"].main()
    output = capsys.readouterr().out
    assert "=== Azure Runtime Economics ===" not in output
    summary = json.loads(
        (tmp_path / "runs" / "snapshot-test-run" / "summary.json").read_text(encoding="utf-8")
    )
    assert "azure_runtime_cost" not in summary
    assert "azure_runtime_modeled_economics" not in summary


def test_execution_console_without_snapshot_clarifies_boundary(runners, capsys):
    evaluation = runners["evaluation"]
    execution = {
        "attempted_interactions": 1, "accepted_interactions": 1,
        "known_direct_execution_cost_usd": 0.01,
        "known_direct_cost_per_attempt_usd": 0.01,
        "known_direct_cost_per_accepted_work_usd": 0.01,
        "measured_tool_calls": 1, "cost_completeness": "partial",
        "unknown_or_unallocated_components": ["azure_ai_search", "observability", "human_recovery"],
    }
    before = deepcopy(execution)
    evaluation._console_printers["print_execution_economics"](execution)
    output = capsys.readouterr().out
    assert "NOT PROVIDED" in output
    assert "Full Execution Cost: NOT YET ESTABLISHED" in output
    assert "Known direct execution cost: $0.010000" in output
    assert execution == before


@pytest.mark.parametrize("runner_name", ["evaluation", "simulation"])
@pytest.mark.parametrize("problem", ["missing_file", "invalid_snapshot", "wrong_workload"])
def test_runner_rejects_bad_snapshot_before_execution(
    runners, saved_snapshot, tmp_path, monkeypatch, runner_name, problem
):
    path, snapshot = saved_snapshot
    if problem == "missing_file":
        path = tmp_path / "missing.json"
    else:
        if problem == "invalid_snapshot":
            snapshot["allocated_azure_runtime_cost_usd"] = 999
        else:
            snapshot["workload_id"] = "other-workload"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [runner_name, "--cost-snapshot", str(path)])

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid snapshot must fail before agent execution")

    monkeypatch.setattr(runners[runner_name], "run_agent_over_cases", forbidden)
    with pytest.raises((OSError, ValueError)):
        runners[runner_name].main()
    assert not (tmp_path / "runs").exists()
