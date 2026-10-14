import json
from copy import deepcopy
from pathlib import Path

import pytest

from foundry_prompt_agent.azure_runtime_cost import (
    load_azure_runtime_cost_config,
    summarize_azure_runtime_cost,
)
from foundry_prompt_agent.cost_snapshot import build_cost_snapshot, save_cost_snapshot
from foundry_prompt_agent.business_economics import (
    load_business_assumptions,
    summarize_business_economics,
)
from foundry_prompt_agent.run_artifacts import (
    build_interaction_records,
    build_run_summary,
    persist_run_package,
    run_dir,
)


def case(name="alpha", category="retrieval", query="q") -> dict:
    return {"name": name, "category": category, "query": query, "ground_truth": "gt"}


def execution_record(interaction_id="alpha", accepted=True) -> dict:
    return {
        "run_id": "run1",
        "workload_id": "contoso-demand-recovery",
        "interaction_id": interaction_id,
        "case_name": interaction_id,
        "category": "retrieval",
        "response_id": "resp_1",
        "model": "gpt-5",
        "input_tokens": 1000,
        "output_tokens": 500,
        "cached_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 1500,
        "model_cost_usd": 0.0034,
        "latency_ms": 123.4,
        "tool_call_count": 1,
        "tool_types": ["azure_ai_search_call"],
        "accepted": accepted,
    }


def business_outcome_record(interaction_id="alpha", accepted=True) -> dict:
    return {
        "run_id": "run1",
        "workload_id": "contoso-demand-recovery",
        "interaction_id": interaction_id,
        "accepted": accepted,
        "customer_engaged_after_response": None,
        "order_completed": None,
        "order_id": None,
        "order_value_usd": None,
        "incremental_order": None,
        "counterfactual_method": None,
        "outcome_evidence_source": None,
        "outcome_observed_at_utc": None,
    }


def pilot_evidence_record(interaction_id="alpha") -> dict:
    return {
        "pilot_id": None,
        "interaction_id": interaction_id,
        "eligible": None,
        "assignment": None,
        "assigned_at_utc": None,
        "staff_unavailable": None,
        "attribution_window_minutes": None,
        "protocol_deviation": None,
        "protocol_deviation_reason": None,
    }


def build(ids=("alpha",)) -> list[dict]:
    return build_interaction_records(
        run_id="run1",
        workload_id="contoso-demand-recovery",
        cases=[case(name=i) for i in ids],
        execution_records=[execution_record(interaction_id=i) for i in ids],
        business_outcome_records=[
            business_outcome_record(interaction_id=i) for i in ids
        ],
        pilot_evidence_records=[
            pilot_evidence_record(interaction_id=i) for i in ids
        ],
    )


def test_consolidated_interaction_preserves_execution_evidence():
    record = build()[0]

    assert record["execution"]["model"] == "gpt-5"
    assert record["execution"]["total_tokens"] == 1500
    assert record["execution"]["tool_types"] == ["azure_ai_search_call"]
    # Identity fields are not duplicated inside the execution block.
    assert "interaction_id" not in record["execution"]
    assert "accepted" not in record["execution"]
    assert record["case"] == {
        "name": "alpha",
        "category": "retrieval",
        "query": "q",
    }


def test_acceptance_remains_distinct():
    record = build()[0]

    assert record["acceptance"] == {"accepted": True}


def test_pilot_unknowns_remain_null():
    record = build()[0]

    assert record["pilot"]["assignment"] is None
    assert record["pilot"]["pilot_id"] is None
    assert "interaction_id" not in record["pilot"]


def test_pilot_exposure_survives_into_interaction():
    exposed_pilot = {
        **pilot_evidence_record("alpha"),
        "assignment": "treatment",
        "exposure": "ai_exposed_to_simulated_customer",
        "evidence_mode": "synthetic_simulation",
        "simulated": True,
    }

    records = build_interaction_records(
        run_id="run1",
        workload_id="w",
        cases=[case(name="alpha")],
        execution_records=[execution_record("alpha")],
        business_outcome_records=[business_outcome_record("alpha")],
        pilot_evidence_records=[exposed_pilot],
        run_mode="simulation",
    )

    pilot = records[0]["pilot"]
    assert pilot["exposure"] == "ai_exposed_to_simulated_customer"
    assert pilot["evidence_mode"] == "synthetic_simulation"
    assert pilot["simulated"] is True
    assert records[0]["run_mode"] == "simulation"


def test_business_outcome_unknowns_remain_null():
    record = build()[0]

    assert record["business_outcome"]["order_completed"] is None
    assert record["business_outcome"]["outcome_evidence_source"] is None
    # Acceptance lives only in the acceptance block.
    assert "accepted" not in record["business_outcome"]


def test_business_outcome_omits_redundant_identity_fields():
    record = build()[0]

    for field in ("run_id", "workload_id", "interaction_id"):
        assert field not in record["business_outcome"]


def test_extra_dataset_case_without_execution_fails():
    with pytest.raises(ValueError):
        build_interaction_records(
            run_id="run1",
            workload_id="w",
            # An extra case "beta" has no matching execution record.
            cases=[case(name="alpha"), case(name="beta")],
            execution_records=[execution_record("alpha")],
            business_outcome_records=[business_outcome_record("alpha")],
            pilot_evidence_records=[pilot_evidence_record("alpha")],
        )


def test_all_four_identity_sets_matching_succeeds():
    records = build(ids=("alpha", "beta"))

    assert {r["interaction_id"] for r in records} == {"alpha", "beta"}



def test_interaction_join_is_by_id_not_ordering():
    records = build_interaction_records(
        run_id="run1",
        workload_id="w",
        cases=[case(name="alpha"), case(name="beta")],
        execution_records=[
            execution_record("alpha"),
            execution_record("beta"),
        ],
        # Side records arrive in a different order.
        business_outcome_records=[
            business_outcome_record("beta"),
            business_outcome_record("alpha"),
        ],
        pilot_evidence_records=[
            pilot_evidence_record("beta"),
            pilot_evidence_record("alpha"),
        ],
    )

    by_id = {r["interaction_id"]: r for r in records}
    assert set(by_id) == {"alpha", "beta"}


def test_duplicate_execution_identity_fails_loudly():
    with pytest.raises(ValueError):
        build_interaction_records(
            run_id="run1",
            workload_id="w",
            cases=[case(name="alpha")],
            execution_records=[
                execution_record("alpha"),
                execution_record("alpha"),
            ],
            business_outcome_records=[business_outcome_record("alpha")],
            pilot_evidence_records=[pilot_evidence_record("alpha")],
        )


def test_mismatched_identity_fails_loudly():
    with pytest.raises(ValueError):
        build_interaction_records(
            run_id="run1",
            workload_id="w",
            cases=[case(name="alpha")],
            execution_records=[execution_record("alpha")],
            business_outcome_records=[business_outcome_record("ghost")],
            pilot_evidence_records=[pilot_evidence_record("alpha")],
        )


def summary_sections(*, cost_snapshot=None, cost_snapshot_path=None) -> dict:
    return build_run_summary(
        run_id="run1",
        workload_id="contoso-demand-recovery",
        execution_economics={"cost_completeness": "partial"},
        modeled_business_economics={"ai_value_multiple": 134.7},
        economic_value={"value_evidence_status": "modeled_only"},
        incremental_economics={"economics_status": "not_established"},
        value_resilience={"resilience_scope": "modeled_scenario"},
        workload_assessment={"assessment_status": "evidence_incomplete"},
        decision_gates={"eligible_actions": ["prove"]},
        portfolio_action={"selected_action": "prove"},
        cost_snapshot=cost_snapshot,
        cost_snapshot_path=cost_snapshot_path,
    )


def test_summary_preserves_all_run_level_sections():
    summary = summary_sections()

    for section in (
        "execution_economics",
        "modeled_business_economics",
        "economic_value",
        "incremental_economics",
        "value_resilience",
        "workload_assessment",
        "decision_gates",
        "portfolio_action",
    ):
        assert section in summary

    # Values are passed through unchanged.
    assert summary["economic_value"]["value_evidence_status"] == "modeled_only"
    assert summary["portfolio_action"]["selected_action"] == "prove"


def test_summary_evidence_mode_is_explicit():
    regression = summary_sections()
    simulation = build_run_summary(
        run_id="run2",
        workload_id="w",
        execution_economics={},
        modeled_business_economics={},
        economic_value={},
        incremental_economics={},
        value_resilience={},
        workload_assessment={},
        decision_gates={},
        portfolio_action={},
        run_mode="simulation",
        evidence_mode="synthetic_simulation",
        simulation={"seed": 42, "count": 20, "generator_version": "1"},
    )

    assert regression["run_mode"] == "regression"
    assert regression["evidence_mode"] == "measured_regression"
    assert simulation["run_mode"] == "simulation"
    assert simulation["evidence_mode"] == "synthetic_simulation"
    assert simulation["simulation"]["seed"] == 42


def test_synthetic_sections_pass_through_and_default_null():
    regression = summary_sections()
    experiment = {"treatment_count": 16, "control_count": 4, "evidence": "x"}
    economics = {"economic_basis_id": "synthetic-run1"}
    simulation = build_run_summary(
        run_id="run2",
        workload_id="w",
        execution_economics={},
        modeled_business_economics={},
        economic_value={},
        incremental_economics={},
        value_resilience={},
        workload_assessment={},
        decision_gates={},
        portfolio_action={},
        run_mode="simulation",
        evidence_mode="synthetic_simulation",
        synthetic_experiment=experiment,
        synthetic_economics=economics,
    )

    # Regression defaults both synthetic sections to null.
    assert regression["synthetic_experiment"] is None
    assert regression["synthetic_economics"] is None
    # Simulation passes them through verbatim (not recalculated).
    assert simulation["synthetic_experiment"] == experiment
    assert simulation["synthetic_economics"] == economics


def test_persistence_layer_does_not_recalculate_economics():
    original = {"ai_value_multiple": 134.7, "recovered_contribution_per_month": 1890.0}
    summary = build_run_summary(
        run_id="run1",
        workload_id="w",
        execution_economics={},
        modeled_business_economics=original,
        economic_value={},
        incremental_economics={},
        value_resilience={},
        workload_assessment={},
        decision_gates={},
        portfolio_action={},
    )

    assert summary["modeled_business_economics"] == original


def test_nested_output_is_json_serializable():
    records = build(ids=("alpha", "beta"))
    summary = summary_sections()

    # Should not raise.
    json.dumps(records)
    json.dumps(summary)


def test_run_directory_is_deterministic_from_run_id(tmp_path):
    directory = run_dir("20260921", base=tmp_path)

    assert directory == tmp_path / "20260921"


def test_persist_run_package_writes_both_files(tmp_path):
    records = build()
    summary = summary_sections()

    interactions_path, summary_path = persist_run_package(
        "run1", records, summary, base=tmp_path
    )

    assert interactions_path == tmp_path / "run1" / "interactions.jsonl"
    assert summary_path == tmp_path / "run1" / "summary.json"

    lines = interactions_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["interaction_id"] == "alpha"
    assert json.loads(summary_path.read_text(encoding="utf-8"))["run_id"] == "run1"


@pytest.fixture
def monthly_snapshot():
    config_path = Path(__file__).resolve().parents[1] / "economics" / "azure_runtime_cost.yaml"
    return build_cost_snapshot(azure_runtime_cost=summarize_azure_runtime_cost(
        load_azure_runtime_cost_config(config_path)
    ))


def test_no_snapshot_leaves_run_summary_unchanged():
    default = summary_sections()
    assert default == summary_sections(cost_snapshot=None, cost_snapshot_path=None)
    assert "azure_runtime_cost" not in default
    assert "azure_runtime_modeled_economics" not in default


@pytest.mark.parametrize("source_type", ["azure_cost_management_manual", "azure_cost_management_api"])
def test_run_package_persists_compact_period_evidence(monthly_snapshot, tmp_path, source_type):
    monthly_snapshot["evidence_source"]["type"] = source_type
    path = tmp_path / "cost_snapshots" / f"{monthly_snapshot['snapshot_id']}.json"
    save_cost_snapshot(monthly_snapshot, path)
    summary = summary_sections(cost_snapshot=monthly_snapshot, cost_snapshot_path=path)
    _, summary_path = persist_run_package("run1", build(), summary, base=tmp_path / "runs")
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    evidence = saved["azure_runtime_cost"]
    for field in (
        "snapshot_id", "workload_id", "cost_period", "created_at", "period_days",
        "allocation_status", "evidence_source", "actual_selected_resource_cost_usd",
        "allocated_azure_runtime_cost_usd", "allocated_azure_runtime_cost_per_day_usd",
    ):
        assert evidence[field] == monthly_snapshot[field]
    assert evidence["snapshot_path"] == str(path)
    assert "resource_allocations" not in evidence
    assert evidence["snapshot_id"] != saved["run_id"]
    assert not any("run_" in field for field in evidence)
    assert "azure_runtime_modeled_economics" not in saved


def test_summary_cost_evidence_is_detached_from_input(monthly_snapshot):
    before = deepcopy(monthly_snapshot)
    summary = summary_sections(cost_snapshot=monthly_snapshot)
    assert monthly_snapshot == before
    summary["azure_runtime_cost"]["cost_period"]["start"] = "changed"
    summary["azure_runtime_cost"]["evidence_source"]["type"] = "changed"
    assert monthly_snapshot == before


@pytest.mark.parametrize("modeled", [
    {},
    {"recovered_contribution_per_month": 1701, "ai_value_multiple": 117.8},
    {"recovered_contribution_per_month": 1701, "days_per_month": 12, "ai_value_multiple": 117.8},
])
def test_snapshot_does_not_invent_monthly_economics_or_customer_value(monthly_snapshot, modeled):
    value = {
        "customer_net_economic_value_usd": None,
        "customer_cost_completeness": None,
        "value_evidence_status": "modeled_only",
    }
    before_modeled = deepcopy(modeled)
    before_value = deepcopy(value)
    summary = build_run_summary(
        run_id="run1", workload_id=monthly_snapshot["workload_id"],
        execution_economics={}, modeled_business_economics=modeled, economic_value=value,
        incremental_economics={}, value_resilience={}, workload_assessment={},
        decision_gates={}, portfolio_action={}, cost_snapshot=monthly_snapshot,
    )
    assert summary["modeled_business_economics"] == before_modeled
    assert summary["economic_value"] == before_value
    assert modeled == before_modeled
    assert value == before_value
    assert "azure_runtime_modeled_economics" not in summary
    assert not any("realized" in key or "roi" in key for key in summary["azure_runtime_cost"])


def test_run_rejects_wrong_workload_snapshot(monthly_snapshot):
    monthly_snapshot["workload_id"] = "other-workload"
    with pytest.raises(ValueError, match="workload_id"):
        summary_sections(cost_snapshot=monthly_snapshot)


def test_run_rejects_invalid_snapshot(monthly_snapshot):
    monthly_snapshot["allocated_azure_runtime_cost_usd"] = 999
    with pytest.raises(ValueError, match="allocated_azure_runtime_cost_usd"):
        summary_sections(cost_snapshot=monthly_snapshot)


def test_snapshot_reference_requires_loaded_evidence(tmp_path):
    with pytest.raises(ValueError, match="requires a loaded"):
        summary_sections(cost_snapshot_path=tmp_path / "snapshot.json")


@pytest.fixture
def live_monthly_snapshot():
    config_path = Path(__file__).resolve().parents[1] / "economics" / "azure_runtime_cost.yaml"
    config = load_azure_runtime_cost_config(config_path)
    config["source"]["type"] = "azure_cost_management_api"
    for index, amount in enumerate([241.92, 4.123483, 0.018399, 0]):
        resource = config["resources"][index]
        resource["actual_cost_usd"] = amount
        resource["cost_evidence_status"] = (
            "no_direct_charge_returned" if index == 3 else "observed_billing"
        )
    return build_cost_snapshot(azure_runtime_cost=summarize_azure_runtime_cost(config))


@pytest.fixture
def regression_business():
    assumptions_path = Path(__file__).resolve().parents[1] / "economics" / "business_assumptions.yaml"
    return summarize_business_economics(
        **load_business_assumptions(assumptions_path),
        success_rate=0.9, cost_per_task_usd=0.0061518,
    )


def runtime_run_summary(snapshot, business, *, days_per_month=None):
    return build_run_summary(
        run_id="run1", workload_id="contoso-demand-recovery",
        execution_economics={
            "known_direct_execution_cost_usd": 0.061518,
            "cost_completeness": "partial",
        },
        modeled_business_economics=business,
        economic_value={
            "modeled_ai_value_multiple": business.get("ai_value_multiple"),
            "customer_net_economic_value_usd": None,
            "total_relevant_customer_cost_usd": None,
            "customer_cost_completeness": None,
        },
        incremental_economics={"economics_status": "not_established"},
        value_resilience={}, workload_assessment={},
        decision_gates={"eligible_actions": ["prove"]},
        portfolio_action={"selected_action": "prove"},
        cost_snapshot=snapshot,
        modeled_business_days_per_month=days_per_month,
    )


def test_monthly_runtime_lens_is_separate_and_persisted(live_monthly_snapshot, regression_business, tmp_path):
    before_snapshot = deepcopy(live_monthly_snapshot)
    before_business = deepcopy(regression_business)
    baseline = runtime_run_summary(None, regression_business, days_per_month=30)
    summary = runtime_run_summary(live_monthly_snapshot, regression_business, days_per_month=30)
    runtime = summary["azure_runtime_modeled_economics"]
    assert runtime["modeled_recovered_contribution_usd"] == pytest.approx(1701)
    assert runtime["allocated_azure_runtime_cost_usd"] == pytest.approx(52.525882)
    assert runtime["modeled_contribution_after_azure_runtime_usd"] == pytest.approx(1648.474118)
    assert runtime["modeled_azure_runtime_value_multiple"] == pytest.approx(1701 / 52.525882)
    assert runtime["cost_period"] == live_monthly_snapshot["cost_period"]
    assert runtime["allocation_status"] == "partially_allocated"
    assert runtime["cost_source"] == live_monthly_snapshot["evidence_source"]
    assert summary["modeled_business_economics"]["ai_inference_cost_per_month"] == pytest.approx(11.07324)
    assert summary["modeled_business_economics"]["ai_value_multiple"] == regression_business["ai_value_multiple"]
    assert summary["execution_economics"]["known_direct_execution_cost_usd"] == 0.061518
    assert summary["execution_economics"]["cost_completeness"] == "partial"
    for section in baseline:
        assert summary[section] == baseline[section]
    assert live_monthly_snapshot == before_snapshot
    assert regression_business == before_business
    assert not any(
        forbidden in field for field in runtime
        for forbidden in ("roi", "realized", "incremental", "customer_net", "run_cost")
    )
    _, path = persist_run_package("run1", [], summary, base=tmp_path)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["azure_runtime_modeled_economics"] == runtime
    assert persisted["azure_runtime_cost"]["snapshot_id"] == live_monthly_snapshot["snapshot_id"]
    assert persisted["economic_value"]["customer_net_economic_value_usd"] is None
    assert persisted["incremental_economics"]["economics_status"] == "not_established"


@pytest.mark.parametrize("days", [None, 12, 28, 31, True, 0])
def test_incompatible_projection_preserves_cost_only(live_monthly_snapshot, regression_business, days):
    summary = runtime_run_summary(live_monthly_snapshot, regression_business, days_per_month=days)
    assert "azure_runtime_cost" in summary
    assert "azure_runtime_modeled_economics" not in summary


@pytest.mark.parametrize("business", [{}, {"recovered_contribution_per_month": None}])
def test_missing_numerator_preserves_cost_only(live_monthly_snapshot, business):
    summary = runtime_run_summary(live_monthly_snapshot, business, days_per_month=30)
    assert "azure_runtime_cost" in summary
    assert "azure_runtime_modeled_economics" not in summary


def test_zero_runtime_cost_uses_existing_helper_convention(regression_business):
    config_path = Path(__file__).resolve().parents[1] / "economics" / "azure_runtime_cost.yaml"
    config = load_azure_runtime_cost_config(config_path)
    for resource in config["resources"]:
        resource["actual_cost_usd"] = 0
    snapshot = build_cost_snapshot(azure_runtime_cost=summarize_azure_runtime_cost(config))
    summary = runtime_run_summary(snapshot, regression_business, days_per_month=30)
    runtime = summary["azure_runtime_modeled_economics"]
    assert runtime["modeled_azure_runtime_value_multiple"] == float("inf")
    assert runtime["modeled_contribution_after_azure_runtime_usd"] == regression_business["recovered_contribution_per_month"]
