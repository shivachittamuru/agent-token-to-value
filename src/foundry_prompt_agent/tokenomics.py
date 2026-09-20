PRICING = {
    # USD per 1M tokens, as of 2026-08-14. Update when model pricing changes.
    "gpt-5": {"input": 1.25, "cached": 0.125, "output": 10.00},
}

# Step 2: Token Cost
def compute_cost(usage: dict) -> float:
    rates = PRICING[usage["model"]]  # KeyError here is a feature: unknown model = unpriced spend
    billed_input = usage["input_tokens"] - usage["cached_tokens"]
    return (
        billed_input / 1_000_000 * rates["input"]
        + usage["cached_tokens"] / 1_000_000 * rates["cached"]
        + usage["output_tokens"] / 1_000_000 * rates["output"]
    )

# Step 3: Token Efficiency
def summarize_efficiency(usages: list[dict]) -> dict:
    tasks = len(usages)
    if tasks == 0:
        return {
            "tasks": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "tokens_per_task": 0.0,
            "input_tokens_per_task": 0.0,
            "output_tokens_per_task": 0.0,
            "cost_per_task": 0.0,
        }

    total_tokens = sum(u["total_tokens"] for u in usages)
    total_input = sum(u["input_tokens"] for u in usages)
    total_output = sum(u["output_tokens"] for u in usages)
    total_cost = sum(compute_cost(u) for u in usages)

    return {
        "tasks": tasks,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "tokens_per_task": total_tokens / tasks,
        "input_tokens_per_task": total_input / tasks,
        "output_tokens_per_task": total_output / tasks,
        "cost_per_task": total_cost / tasks,
    }


def summarize_effectiveness(efficiency: dict, success_rate: float) -> dict:
    if success_rate <= 0:
        return {
            "success_rate": success_rate,
            "successful_tasks": 0.0,
            "tokens_per_success": float("inf"),
            "cost_per_success": float("inf"),
        }

    return {
        "success_rate": success_rate,
        "successful_tasks": success_rate * efficiency["tasks"],
        "tokens_per_success": efficiency["tokens_per_task"] / success_rate,
        "cost_per_success": efficiency["cost_per_task"] / success_rate,
    }


def summarize_accepted_work(
    efficiency: dict,
    *,
    accepted_interactions: int,
    attempted_interactions: int,
) -> dict:
    """Derive Accepted Work token economics from observed interaction counts.

    Accepted Work is a stricter signal than the behavior pass rate: an
    interaction only counts when it satisfies the behavior rubric and every
    mandatory guardrail. Both counts are observed upstream from row-level
    results; this function only converts them into token economics. The
    denominator is the actual number of workload attempts, so interactions
    with no acceptance evidence are treated conservatively (not accepted).
    Zero accepted work yields infinite unit costs.
    """

    accepted_work_rate = (
        accepted_interactions / attempted_interactions
        if attempted_interactions
        else 0.0
    )

    if accepted_interactions <= 0:
        return {
            "attempted_interactions": attempted_interactions,
            "accepted_interactions": accepted_interactions,
            "accepted_work_rate": accepted_work_rate,
            "tokens_per_accepted_work": float("inf"),
            "cost_per_accepted_work": float("inf"),
        }

    return {
        "attempted_interactions": attempted_interactions,
        "accepted_interactions": accepted_interactions,
        "accepted_work_rate": accepted_work_rate,
        "tokens_per_accepted_work": (
            efficiency["total_tokens"] / accepted_interactions
        ),
        "cost_per_accepted_work": (
            efficiency["total_cost"] / accepted_interactions
        ),
    }

