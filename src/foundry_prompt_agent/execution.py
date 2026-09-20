"""Pure Execution Record building and Accepted Work join logic.

Execution Records preserve observable per-interaction execution evidence
(identifiers, measured tokens, model cost, latency, and tool-call evidence)
before any attempt at full-system costing. All Azure/SDK measurement happens
upstream in ``agent.py``; this module stays pure and testable.
"""

from __future__ import annotations

from foundry_prompt_agent.tokenomics import compute_cost

WORKLOAD_ID = "contoso-demand-recovery"


def build_execution_record(
    *,
    run_id: str,
    interaction_id: str,
    case: dict,
    execution: dict,
) -> dict:
    """Build one Execution Record for a case, with acceptance still unknown.

    Model cost is derived from the same measured token fields via the shared
    pricing in ``tokenomics.compute_cost`` to avoid duplicating pricing logic.
    Unknown tool evidence (None) is preserved as-is, never coerced to zero.
    """

    return {
        "run_id": run_id,
        "workload_id": WORKLOAD_ID,
        "interaction_id": interaction_id,
        "case_name": case["name"],
        "category": case.get("category"),
        "agent_name": execution["agent_name"],
        "agent_version": execution["agent_version"],
        "response_id": execution["response_id"],
        "model": execution["model"],
        "input_tokens": execution["input_tokens"],
        "output_tokens": execution["output_tokens"],
        "cached_tokens": execution["cached_tokens"],
        "reasoning_tokens": execution["reasoning_tokens"],
        "total_tokens": execution["total_tokens"],
        "model_cost_usd": compute_cost(execution),
        "latency_ms": execution["latency_ms"],
        "tool_call_count": execution["tool_call_count"],
        "tool_types": execution["tool_types"],
        "accepted": None,
    }


def build_execution_records(
    run_id: str,
    entries: list[tuple[dict, dict]],
) -> list[dict]:
    """Build records for (case, execution) pairs using a unique join key.

    The case ``name`` is used as the stable ``interaction_id``. Uniqueness is
    enforced so the later Accepted Work join can never rely on positional
    ordering between unrelated collections; a duplicate fails loudly.
    """

    records = []
    seen: set[str] = set()

    for case, execution in entries:
        interaction_id = case["name"]
        if interaction_id in seen:
            raise ValueError(
                f"Duplicate interaction id (case name): {interaction_id}"
            )
        seen.add(interaction_id)

        records.append(
            build_execution_record(
                run_id=run_id,
                interaction_id=interaction_id,
                case=case,
                execution=execution,
            )
        )

    return records


def apply_acceptance(
    records: list[dict],
    acceptance_rows: list[dict],
) -> list[dict]:
    """Join Accepted Work results back onto Execution Records by interaction.

    Acceptance is matched on the stable ``interaction_id``/row ``name`` key,
    not positional order. Records without matching row-level evidence keep
    ``accepted = None`` so genuinely missing evidence stays Unknown.
    """

    accepted_by_id = {
        row["name"]: row["accepted"]
        for row in acceptance_rows
        if row.get("name") is not None
    }

    return [
        {**record, "accepted": accepted_by_id.get(record["interaction_id"])}
        for record in records
    ]
