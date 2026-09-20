import pytest

from foundry_prompt_agent.execution import (
    WORKLOAD_ID,
    apply_acceptance,
    build_execution_record,
    build_execution_records,
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
