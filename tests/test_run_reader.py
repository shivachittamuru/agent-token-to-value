import json

import pytest

from foundry_prompt_agent import dashboard_views as views
from foundry_prompt_agent.run_reader import (
    RunPackageError,
    discover_run_ids,
    latest_run_id,
    load_interactions,
    load_latest_run,
    load_run,
    load_summary,
)


def _write_run(base, run_id, summary, interactions):
    directory = base / run_id
    directory.mkdir(parents=True)
    (directory / "summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    (directory / "interactions.jsonl").write_text(
        "\n".join(json.dumps(r) for r in interactions) + "\n",
        encoding="utf-8",
    )


def regression_summary(run_id="20260101000000") -> dict:
    return {
        "run_id": run_id,
        "workload_id": "contoso-demand-recovery",
        "run_mode": "regression",
        "evidence_mode": "measured_regression",
        "simulation": None,
        "execution_economics": {
            "attempted_interactions": 10,
            "accepted_interactions": 9,
            "known_direct_execution_cost_usd": 0.07,
            "known_direct_cost_per_accepted_work_usd": 0.0078,
            "measured_tool_calls": 14,
            "cost_completeness": "partial",
        },
        "modeled_business_economics": {
            "recovered_contribution_per_month": 1890.0,
            "ai_value_multiple": 134.7,
        },
        "economic_value": {
            "value_evidence_status": "modeled_only",
            "cost_completeness": "partial",
            "customer_net_economic_value_usd": None,
        },
        "incremental_economics": {"economics_status": "not_established"},
        "value_resilience": {
            "resilience_scope": "modeled_scenario",
            "resilience_status": "not_classified",
        },
        "workload_assessment": {
            "technical_performance_status": "established",
            "technical_evidence_scope": "regression",
            "business_outcome_status": "unknown",
            "business_evidence_scope": "regression",
            "incrementality_status": "unknown",
            "incrementality_evidence_scope": "regression",
            "economic_value_status": "modeled_only",
            "incremental_economics_status": "not_established",
            "execution_cost_status": "partial",
            "established_claims": ["Technical behavior established in the regression suite"],
            "simulated_claims": [],
            "modeled_claims": ["modeled"],
            "unknown_claims": ["Real-world business outcomes not observed"],
        },
        "decision_gates": {
            "gates": {
                "value_gate": {"status": "conditional", "rationale": "modeled only"},
                "evidence_gate": {"status": "conditional", "rationale": "weak"},
            },
            "eligible_actions": ["prove", "pause"],
            "ineligible_actions": [{"action": "scale", "rationale": "no"}],
        },
        "portfolio_action": {
            "selected_action": "prove",
            "primary_decision_deficit": "evidence",
            "action_rationale": "PROVE rationale",
            "required_work": ["measure demand"],
            "required_evidence": ["treatment/control conversion"],
            "resource_request": "bounded pilot",
            "reassessment_trigger": "pilot evidence",
        },
    }


def simulation_summary(run_id="20260202000000") -> dict:
    summary = regression_summary(run_id)
    summary["run_mode"] = "simulation"
    summary["evidence_mode"] = "synthetic_simulation"
    summary["simulation"] = {
        "inquiry_seed": 42,
        "outcome_seed": 4201,
        "generator_version": "1",
        "outcome_simulator_version": "1",
    }
    summary["synthetic_experiment"] = {
        "eligible_interactions": 20,
        "treatment_count": 16,
        "control_count": 4,
        "treatment_orders": 1,
        "control_orders": 0,
        "treatment_conversion": 0.0625,
        "control_conversion": 0.0,
        "simulated_conversion_lift_pp": 6.25,
        "evidence_mode": "synthetic_simulation",
        "counterfactual_method": "randomized_synthetic_control",
    }
    summary["synthetic_economics"] = {
        "economic_basis_id": "synthetic-x",
        "simulated_incremental_conversion_rate": 0.0625,
        "simulated_incremental_orders_for_observed_sample": 1.0,
        "average_order_value_usd": 6.08,
        "simulated_incremental_revenue_usd": 6.08,
        "simulated_incremental_contribution_usd": 2.13,
    }
    summary["workload_assessment"].update(
        {
            "technical_evidence_scope": "simulation",
            "business_outcome_status": "observed",
            "business_evidence_scope": "simulation",
            "incrementality_status": "established",
            "incrementality_evidence_scope": "simulation",
            "simulated_claims": ["Business outcomes observed in synthetic simulation"],
        }
    )
    return summary


def interactions(count=2, simulation=False) -> list[dict]:
    rows = []
    for n in range(count):
        rows.append(
            {
                "interaction_id": f"i{n}",
                "run_mode": "simulation" if simulation else "regression",
                "case": {"name": f"i{n}", "category": "exact_retrieval", "query": "q"},
                "execution": {
                    "total_tokens": 1500,
                    "model_cost_usd": 0.003,
                    "latency_ms": 120.0,
                    "tool_call_count": 1,
                },
                "acceptance": {"accepted": True},
                "pilot": {
                    "assignment": ("treatment" if n % 2 == 0 else "control")
                    if simulation
                    else None,
                    "exposure": (
                        "ai_exposed_to_simulated_customer"
                        if simulation and n % 2 == 0
                        else "ai_not_exposed_shadow_execution_only"
                        if simulation
                        else None
                    ),
                },
                "business_outcome": {
                    "order_completed": True if simulation and n == 0 else None,
                    "order_value_usd": 8.0 if simulation and n == 0 else None,
                },
            }
        )
    return rows


# --- run_reader tests ---------------------------------------------------------


def test_discovers_valid_run_packages(tmp_path):
    _write_run(tmp_path, "20260101000000", regression_summary(), interactions())
    (tmp_path / "not_a_run").mkdir()  # missing files -> ignored

    assert discover_run_ids(tmp_path) == ["20260101000000"]


def test_orders_runs_deterministically(tmp_path):
    _write_run(tmp_path, "20260101000000", regression_summary("20260101000000"), interactions())
    _write_run(tmp_path, "20260303000000", regression_summary("20260303000000"), interactions())
    _write_run(tmp_path, "20260202000000", regression_summary("20260202000000"), interactions())

    assert discover_run_ids(tmp_path) == [
        "20260101000000",
        "20260202000000",
        "20260303000000",
    ]
    assert latest_run_id(tmp_path) == "20260303000000"


def test_loads_latest_valid_run(tmp_path):
    _write_run(tmp_path, "20260101000000", regression_summary("20260101000000"), interactions())
    _write_run(tmp_path, "20260202000000", simulation_summary("20260202000000"), interactions(simulation=True))

    run = load_latest_run(tmp_path)
    assert run["run_id"] == "20260202000000"
    assert run["summary"]["run_mode"] == "simulation"


def test_loads_interactions_jsonl(tmp_path):
    _write_run(tmp_path, "r", regression_summary("r"), interactions(count=3))

    assert len(load_interactions("r", tmp_path)) == 3


def test_handles_missing_optional_simulation_sections(tmp_path):
    summary = regression_summary("r")
    # No synthetic_experiment / synthetic_economics keys at all.
    _write_run(tmp_path, "r", summary, interactions())

    run = load_run("r", tmp_path)
    assert views.prove_view(run["summary"]) is None
    assert views.value_view(run["summary"])["synthetic"] is None


def test_malformed_summary_fails_clearly(tmp_path):
    directory = tmp_path / "bad"
    directory.mkdir()
    (directory / "summary.json").write_text("{not json", encoding="utf-8")
    (directory / "interactions.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(RunPackageError):
        load_summary("bad", tmp_path)


def test_structurally_invalid_summary_fails(tmp_path):
    directory = tmp_path / "bad"
    directory.mkdir()
    (directory / "summary.json").write_text(json.dumps({"no": "run_id"}), encoding="utf-8")
    (directory / "interactions.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(RunPackageError):
        load_summary("bad", tmp_path)


def test_no_azure_or_foundry_dependency_in_reader():
    import ast

    import foundry_prompt_agent.run_reader as reader
    import foundry_prompt_agent.dashboard_views as dv

    forbidden = ("azure", "openai", "foundry_prompt_agent.foundry_eval")
    for module in (reader, dv):
        tree = ast.parse(open(module.__file__, encoding="utf-8").read())
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        for name in imported:
            assert not any(name.startswith(bad) for bad in forbidden), name


# --- dashboard_views tests ----------------------------------------------------


def test_regression_journey_reflects_missing_business_evidence():
    summary = regression_summary()
    states = views.journey_states(summary)

    assert states["MEASURE"] == "ESTABLISHED"
    assert states["PROVE"] == "UNKNOWN"
    assert states["VALUE"] == "MODELED"
    assert states["ACT"] == "PROVE"


def test_simulation_recognizes_synthetic_sections():
    summary = simulation_summary()

    assert views.journey_states(summary)["PROVE"] == "SIMULATED"
    assert views.journey_states(summary)["VALUE"] == "SIMULATED / MODELED"
    assert views.prove_view(summary)["treatment_count"] == 16
    assert views.value_view(summary)["synthetic"] is not None


def test_unknown_status_does_not_invent_scope():
    summary = regression_summary()
    rows = {r["dimension"]: r for r in views.test_evidence_rows(summary)}

    business = rows["Business outcome"]
    assert business["status"] == "UNKNOWN"
    assert business["scope"] == views.UNAVAILABLE


def test_simulation_scope_present_for_established_dimensions():
    summary = simulation_summary()
    rows = {r["dimension"]: r for r in views.test_evidence_rows(summary)}

    assert rows["Business outcome"]["status"] == "OBSERVED"
    assert rows["Business outcome"]["scope"] == "SIMULATION"
    assert rows["Incrementality"]["scope"] == "SIMULATION"


def test_interaction_table_preserves_exposure():
    rows = views.interaction_table_rows(interactions(count=2, simulation=True))
    by_assignment = {r["assignment"]: r for r in rows}

    assert by_assignment["treatment"]["exposure"] == "ai_exposed_to_simulated_customer"
    assert (
        by_assignment["control"]["exposure"]
        == "ai_not_exposed_shadow_execution_only"
    )


def test_measure_metrics_handle_zero_denominator():
    summary = regression_summary()
    summary["execution_economics"]["attempted_interactions"] = 0
    summary["execution_economics"]["accepted_interactions"] = 0

    metrics = views.measure_metrics(summary, [])
    assert metrics["acceptance_rate"] == 0.0


def test_presentation_does_not_recalculate_values():
    summary = simulation_summary()
    value = views.value_view(summary)

    # Values pass through verbatim from the stored summary.
    assert value["modeled"]["recovered_contribution_usd"] == 1890.0
    assert value["synthetic"]["simulated_incremental_contribution_usd"] == 2.13
    # Decision-grade stays Unknown; synthetic never feeds it.
    assert value["decision_grade"]["customer_net_economic_value_usd"] is None
    assert value["decision_grade"]["incremental_net_economic_value_usd"] is None


def test_decide_actions_flags_scale_ineligible():
    actions = views.decide_actions(regression_summary())

    assert actions["scale_eligible"] is False
    assert "scale" in actions["ineligible"]
