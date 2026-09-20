import pytest

from foundry_prompt_agent.execution import (
    WORKLOAD_ID,
    apply_acceptance,
    attribute_costs,
    build_execution_record,
    build_execution_records,
    summarize_execution_economics,
)
from foundry_prompt_agent.tokenomics import compute_cost


def execution(
    *,
    response_id="resp_1",
    tool_call_count=1,
    tool_types=None,
    latency_ms=123.4,
) -> dict:
    return {
        "response_id": response_id,
        "agent_name": "foundry-prompt-agent",
        "agent_version": "7",
        "model": "gpt-5",
        "input_tokens": 1_000,
        "output_tokens": 500,
        "cached_tokens": 200,
        "reasoning_tokens": 50,
        "total_tokens": 1_500,
        "latency_ms": latency_ms,
        "tool_call_count": tool_call_count,
        "tool_types": (
            tool_types if tool_types is not None else ["azure_ai_search_call"]
        ),
    }


def case(name="exact_price", category="retrieval") -> dict:
    return {
        "name": name,
        "category": category,
        "query": "q",
        "ground_truth": "gt",
    }


def test_build_execution_record_sets_accepted_none_and_workload():
    record = build_execution_record(
        run_id="run1",
        interaction_id="exact_price",
        case=case(),
        execution=execution(),
    )

    assert record["accepted"] is None
    assert record["workload_id"] == WORKLOAD_ID
    assert record["run_id"] == "run1"
    assert record["interaction_id"] == "exact_price"
    assert record["case_name"] == "exact_price"
    assert record["category"] == "retrieval"


def test_build_execution_record_prices_from_shared_pricing():
    exec_meta = execution()

    record = build_execution_record(
        run_id="run1",
        interaction_id="exact_price",
        case=case(),
        execution=exec_meta,
    )

    assert record["model_cost_usd"] == pytest.approx(compute_cost(exec_meta))


def test_build_execution_record_preserves_unknown_tool_evidence():
    record = build_execution_record(
        run_id="run1",
        interaction_id="exact_price",
        case=case(),
        execution=execution(tool_call_count=None, tool_types=[None]),
    )

    # Unknown must remain Unknown, not zero.
    assert record["tool_call_count"] is None


def test_build_execution_records_rejects_duplicate_interaction_ids():
    entries = [
        (case(name="dup"), execution(response_id="a")),
        (case(name="dup"), execution(response_id="b")),
    ]

    with pytest.raises(ValueError):
        build_execution_records("run1", entries)


def test_apply_acceptance_joins_by_interaction_id_not_position():
    records = build_execution_records(
        "run1",
        [
            (case(name="alpha"), execution(response_id="a")),
            (case(name="beta"), execution(response_id="b")),
        ],
    )

    # Rows arrive in a different order than the records.
    acceptance_rows = [
        {"name": "beta", "accepted": True},
        {"name": "alpha", "accepted": False},
    ]

    joined = apply_acceptance(records, acceptance_rows)
    accepted_by_id = {r["interaction_id"]: r["accepted"] for r in joined}

    assert accepted_by_id["alpha"] is False
    assert accepted_by_id["beta"] is True


def test_apply_acceptance_missing_evidence_stays_none():
    records = build_execution_records(
        "run1",
        [
            (case(name="alpha"), execution(response_id="a")),
            (case(name="beta"), execution(response_id="b")),
        ],
    )

    # Only alpha has row-level evidence; beta's acceptance is genuinely missing.
    joined = apply_acceptance(records, [{"name": "alpha", "accepted": True}])
    accepted_by_id = {r["interaction_id"]: r["accepted"] for r in joined}

    assert accepted_by_id["alpha"] is True
    assert accepted_by_id["beta"] is None


def sample_record(model_cost_usd=0.0034025, tool_call_count=1) -> dict:
    return build_execution_record(
        run_id="run1",
        interaction_id="exact_price",
        case=case(),
        execution=execution(tool_call_count=tool_call_count),
    ) | {"model_cost_usd": model_cost_usd}


def _component(attribution: dict, name: str) -> dict:
    return next(
        c for c in attribution["components"] if c["component"] == name
    )


def test_attribute_costs_includes_measured_model_cost():
    record = sample_record(model_cost_usd=0.0034025)

    attribution = attribute_costs(record)
    model = _component(attribution, "model_inference")

    assert model["evidence_status"] == "measured"
    assert model["attribution_mode"] == "direct"
    assert model["cost_usd"] == pytest.approx(0.0034025)
    assert attribution["known_direct_execution_cost_usd"] == pytest.approx(
        0.0034025
    )


def test_attribute_costs_keeps_search_cost_unknown():
    record = sample_record(tool_call_count=3)

    search = _component(attribute_costs(record), "azure_ai_search")

    # Usage is preserved; per-call pricing is not invented.
    assert search["cost_usd"] is None
    assert "tool_call_count=3" in search["note"]
    assert "azure_ai_search" in (
        attribute_costs(record)["unknown_or_unallocated_components"]
    )


def test_attribute_costs_does_not_coerce_unknown_to_zero():
    attribution = attribute_costs(sample_record())

    for name in ("azure_ai_search", "observability", "human_recovery"):
        assert _component(attribution, name)["cost_usd"] is None

    assert set(attribution["unknown_or_unallocated_components"]) == {
        "azure_ai_search",
        "observability",
        "human_recovery",
    }


def test_attribute_costs_runtime_has_no_additional_fee():
    runtime = _component(attribute_costs(sample_record()), "foundry_agent_runtime")

    assert runtime["cost_usd"] == 0.0
    assert runtime["evidence_status"] == "no_additional_fee"


def test_attribute_costs_not_labelled_full_execution_cost():
    attribution = attribute_costs(sample_record())

    # Known direct cost must not be mislabelled as a complete execution cost.
    assert attribution["cost_completeness"] == "partial"
    assert "full_execution_cost_usd" not in attribution
    assert "full_execution_cost" not in attribution
    assert attribution["unknown_or_unallocated_components"]


def economics_record(
    *,
    name: str,
    accepted,
    model_cost_usd: float = 0.001,
    tool_call_count=1,
) -> dict:
    record = build_execution_record(
        run_id="run1",
        interaction_id=name,
        case=case(name=name),
        execution=execution(tool_call_count=tool_call_count),
    )
    return record | {
        "accepted": accepted,
        "model_cost_usd": model_cost_usd,
    }


def summarize(records: list[dict]) -> dict:
    attributions = [attribute_costs(record) for record in records]
    return summarize_execution_economics(records, attributions)


def test_summarize_execution_economics_normal_accepted_case():
    records = [
        economics_record(name="a", accepted=True, model_cost_usd=0.001),
        economics_record(name="b", accepted=True, model_cost_usd=0.003),
    ]

    summary = summarize(records)

    assert summary["attempted_interactions"] == 2
    assert summary["accepted_interactions"] == 2
    assert summary["known_direct_execution_cost_usd"] == pytest.approx(0.004)
    assert summary["known_direct_cost_per_attempt_usd"] == pytest.approx(0.002)
    assert summary[
        "known_direct_cost_per_accepted_work_usd"
    ] == pytest.approx(0.002)


def test_summarize_execution_economics_rejected_work_raises_cost_per_accepted():
    records = [
        economics_record(name="a", accepted=True, model_cost_usd=0.002),
        economics_record(name="b", accepted=False, model_cost_usd=0.002),
    ]

    summary = summarize(records)

    # Cost is incurred for both attempts but only one is accepted work.
    assert summary["accepted_interactions"] == 1
    assert summary["known_direct_cost_per_attempt_usd"] == pytest.approx(0.002)
    assert summary[
        "known_direct_cost_per_accepted_work_usd"
    ] == pytest.approx(0.004)
    assert (
        summary["known_direct_cost_per_accepted_work_usd"]
        > summary["known_direct_cost_per_attempt_usd"]
    )


def test_summarize_execution_economics_zero_accepted_is_infinite():
    records = [
        economics_record(name="a", accepted=False),
        economics_record(name="b", accepted=None),
    ]

    summary = summarize(records)

    assert summary["accepted_interactions"] == 0
    assert summary["known_direct_cost_per_accepted_work_usd"] == float("inf")


def test_summarize_execution_economics_aggregates_measured_tool_calls():
    records = [
        economics_record(name="a", accepted=True, tool_call_count=1),
        economics_record(name="b", accepted=True, tool_call_count=2),
        economics_record(name="c", accepted=True, tool_call_count=None),
    ]

    summary = summarize(records)

    # Unknown tool evidence is skipped, not counted as zero dollars.
    assert summary["measured_tool_calls"] == 3


def test_summarize_execution_economics_unique_unknown_components():
    records = [
        economics_record(name="a", accepted=True),
        economics_record(name="b", accepted=True),
    ]

    summary = summarize(records)

    assert summary["unknown_or_unallocated_components"] == [
        "azure_ai_search",
        "human_recovery",
        "observability",
    ]


def test_summarize_execution_economics_partial_has_no_full_cost_field():
    records = [economics_record(name="a", accepted=True)]

    summary = summarize(records)

    assert summary["cost_completeness"] == "partial"
    assert "full_execution_cost" not in summary
    assert "full_execution_cost_usd" not in summary
    assert "total_execution_cost_usd" not in summary
    assert "total_customer_cost_usd" not in summary
