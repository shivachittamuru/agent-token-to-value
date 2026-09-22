import json

import pytest

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


def summary_sections() -> dict:
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
