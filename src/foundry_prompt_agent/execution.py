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


def build_cost_components(record: dict) -> list[dict]:
    """Describe attributable cost components for one Execution Record.

    Each component states its evidence and how (or whether) it is attributed,
    so Unknown or unpriced components stay explicit rather than being coerced
    to zero. Only model inference is measured and directly priced today.
    """

    return [
        {
            "component": "model_inference",
            "evidence_status": "measured",
            "attribution_mode": "direct",
            "cost_behavior": "variable",
            "cost_usd": record["model_cost_usd"],
            "note": "Measured token usage priced by the model rate card.",
        },
        {
            "component": "azure_ai_search",
            "evidence_status": "usage_measured_unpriced",
            "attribution_mode": "usage_based",
            "cost_behavior": "variable",
            "cost_usd": None,
            "note": (
                f"tool_call_count={record.get('tool_call_count')}; "
                "Search SKU/pricing model and allocation rule not yet known."
            ),
        },
        {
            "component": "foundry_agent_runtime",
            "evidence_status": "no_additional_fee",
            "attribution_mode": "direct",
            "cost_behavior": "none",
            "cost_usd": 0.0,
            "note": (
                "Native Foundry prompt agent adds no separate runtime fee "
                "beyond separately billed model/tool resources. Does not "
                "generalize to hosted agents."
            ),
        },
        {
            "component": "observability",
            "evidence_status": "unknown",
            "attribution_mode": "allocated",
            "cost_behavior": "shared",
            "cost_usd": None,
            "note": "Platform observability not yet allocated to this workload.",
        },
        {
            "component": "human_recovery",
            "evidence_status": "unknown",
            "attribution_mode": "unknown",
            "cost_behavior": "variable",
            "cost_usd": None,
            "note": "No measured human review/escalation rate or cost yet.",
        },
    ]


def attribute_costs(record: dict) -> dict:
    """Build a Cost Attribution Record from one Execution Record.

    Sums only known, directly attributed costs. Any component with an unknown
    or unallocated cost is surfaced explicitly, and the result is never
    labelled a full execution cost while anything remains Unknown.
    """

    components = build_cost_components(record)

    known_direct = sum(
        component["cost_usd"]
        for component in components
        if component["cost_usd"] is not None
        and component["attribution_mode"] == "direct"
    )

    unknown_or_unallocated = [
        component["component"]
        for component in components
        if component["cost_usd"] is None
    ]

    return {
        "run_id": record["run_id"],
        "interaction_id": record["interaction_id"],
        "components": components,
        "known_direct_execution_cost_usd": known_direct,
        "unknown_or_unallocated_components": unknown_or_unallocated,
        "cost_completeness": "partial" if unknown_or_unallocated else "complete",
    }
