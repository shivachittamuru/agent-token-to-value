import pytest

from foundry_prompt_agent.tokenomics import (
    PRICING,
    compute_cost,
    summarize_accepted_work,
    summarize_effectiveness,
    summarize_efficiency,
)


def usage(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> dict:
    return {
        "model": "gpt-5",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cached_tokens": cached_tokens,
        "reasoning_tokens": 0,
    }


def test_compute_cost_charges_fresh_cached_and_output_separately():
    cost = compute_cost(usage(1_000, 500, cached_tokens=200))

    expected = (
        800 / 1_000_000 * PRICING["gpt-5"]["input"]
        + 200 / 1_000_000 * PRICING["gpt-5"]["cached"]
        + 500 / 1_000_000 * PRICING["gpt-5"]["output"]
    )

    assert cost == pytest.approx(expected)


def test_compute_cost_discounts_cached_input():
    fresh = compute_cost(usage(1_000, 0))
    cached = compute_cost(usage(1_000, 0, cached_tokens=1_000))

    assert cached < fresh


def test_compute_cost_rejects_unpriced_model():
    unpriced = usage(100, 100)
    unpriced["model"] = "unknown-model"

    with pytest.raises(KeyError):
        compute_cost(unpriced)


def test_summarize_efficiency_averages_per_task():
    summary = summarize_efficiency(
        [
            usage(1_000, 500),
            usage(3_000, 1_500),
        ]
    )

    assert summary["tasks"] == 2
    assert summary["total_tokens"] == 6_000
    assert summary["tokens_per_task"] == pytest.approx(3_000)
    assert summary["input_tokens_per_task"] == pytest.approx(2_000)
    assert summary["output_tokens_per_task"] == pytest.approx(1_000)
    assert summary["cost_per_task"] == pytest.approx(
        summary["total_cost"] / 2
    )


def test_summarize_efficiency_handles_empty_usage():
    summary = summarize_efficiency([])

    assert summary["tasks"] == 0
    assert summary["total_tokens"] == 0
    assert summary["total_cost"] == 0.0
    assert summary["tokens_per_task"] == 0.0
    assert summary["cost_per_task"] == 0.0


def test_summarize_effectiveness_scales_cost_by_success_rate():
    efficiency = summarize_efficiency([usage(1_000, 500), usage(1_000, 500)])

    effectiveness = summarize_effectiveness(efficiency, 0.5)

    assert effectiveness["successful_tasks"] == pytest.approx(1.0)
    assert effectiveness["tokens_per_success"] == pytest.approx(
        efficiency["tokens_per_task"] / 0.5
    )
    assert effectiveness["cost_per_success"] == pytest.approx(
        efficiency["cost_per_task"] / 0.5
    )


def test_summarize_effectiveness_with_zero_success_is_infinite():
    efficiency = summarize_efficiency([usage(1_000, 500)])

    effectiveness = summarize_effectiveness(efficiency, 0.0)

    assert effectiveness["successful_tasks"] == 0.0
    assert effectiveness["tokens_per_success"] == float("inf")
    assert effectiveness["cost_per_success"] == float("inf")


def test_summarize_accepted_work_scales_cost_by_accepted_count():
    efficiency = summarize_efficiency([usage(1_000, 500), usage(1_000, 500)])

    accepted = summarize_accepted_work(
        efficiency, accepted_interactions=1, attempted_interactions=2
    )

    assert accepted["accepted_work_rate"] == pytest.approx(0.5)
    assert accepted["tokens_per_accepted_work"] == pytest.approx(
        efficiency["total_tokens"] / 1
    )
    assert accepted["cost_per_accepted_work"] == pytest.approx(
        efficiency["total_cost"] / 1
    )


def test_summarize_accepted_work_full_acceptance_matches_efficiency():
    efficiency = summarize_efficiency([usage(1_000, 500), usage(3_000, 1_500)])

    accepted = summarize_accepted_work(
        efficiency, accepted_interactions=2, attempted_interactions=2
    )

    assert accepted["accepted_work_rate"] == pytest.approx(1.0)
    assert accepted["tokens_per_accepted_work"] == pytest.approx(
        efficiency["tokens_per_task"]
    )
    assert accepted["cost_per_accepted_work"] == pytest.approx(
        efficiency["cost_per_task"]
    )


def test_summarize_accepted_work_denominator_is_attempts_not_evaluated():
    efficiency = summarize_efficiency([usage(1_000, 500), usage(1_000, 500)])

    # Only one interaction was accepted out of three attempted, even though
    # fewer rows may have been evaluated upstream.
    accepted = summarize_accepted_work(
        efficiency, accepted_interactions=1, attempted_interactions=3
    )

    assert accepted["accepted_work_rate"] == pytest.approx(1 / 3)
    assert accepted["tokens_per_accepted_work"] == pytest.approx(
        efficiency["total_tokens"] / 1
    )


def test_summarize_accepted_work_with_zero_acceptance_is_infinite():
    efficiency = summarize_efficiency([usage(1_000, 500)])

    accepted = summarize_accepted_work(
        efficiency, accepted_interactions=0, attempted_interactions=1
    )

    assert accepted["accepted_work_rate"] == pytest.approx(0.0)
    assert accepted["tokens_per_accepted_work"] == float("inf")
    assert accepted["cost_per_accepted_work"] == float("inf")
