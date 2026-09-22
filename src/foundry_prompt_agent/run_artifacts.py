"""Run-centric evidence package persistence.

Consolidates the per-interaction and run-level evidence produced by the domain
modules into a single ``runs/<run_id>/`` package (``interactions.jsonl`` and
``summary.json``). This layer only reshapes and writes existing records; it
never recalculates economics or decision logic, and it preserves Unknown as
``null``.
"""

from __future__ import annotations

import json
from pathlib import Path

RUNS_DIR = Path("runs")

# Fields that identify or belong elsewhere in the consolidated record and are
# therefore excluded from the nested ``execution`` block.
_EXECUTION_OMIT = frozenset(
    {"run_id", "workload_id", "interaction_id", "case_name", "category", "accepted"}
)


def _index_by(records: list[dict], *, key: str, label: str) -> dict:
    index: dict = {}
    for record in records:
        identity = record.get(key)
        if identity is None:
            raise ValueError(f"{label} record is missing {key}")
        if identity in index:
            raise ValueError(f"Duplicate {label} {key}: {identity!r}")
        index[identity] = record
    return index


def _consolidate_interaction(
    *,
    run_id: str,
    workload_id: str,
    interaction_id: str,
    case: dict,
    execution_record: dict,
    business_outcome_record: dict,
    pilot_evidence_record: dict,
) -> dict:
    execution = {
        key: value
        for key, value in execution_record.items()
        if key not in _EXECUTION_OMIT
    }
    business_outcome = {
        key: value
        for key, value in business_outcome_record.items()
        if key not in {"run_id", "workload_id", "interaction_id", "accepted"}
    }
    pilot = {
        key: value
        for key, value in pilot_evidence_record.items()
        if key != "interaction_id"
    }

    return {
        "run_id": run_id,
        "workload_id": workload_id,
        "interaction_id": interaction_id,
        "case": {
            "name": case["name"],
            "category": case.get("category"),
            "query": case.get("query"),
        },
        "execution": execution,
        "acceptance": {"accepted": execution_record.get("accepted")},
        "pilot": pilot,
        "business_outcome": business_outcome,
    }


def build_interaction_records(
    *,
    run_id: str,
    workload_id: str,
    cases: list[dict],
    execution_records: list[dict],
    business_outcome_records: list[dict],
    pilot_evidence_records: list[dict],
    run_mode: str = "regression",
) -> list[dict]:
    """Join per-interaction evidence into consolidated records by identity.

    Joins are by ``interaction_id`` (the case ``name``), never positional
    order. Duplicate execution identities, and side records that do not match
    an execution interaction, both fail loudly. ``run_mode`` provenance is
    stamped on every record.
    """

    case_by_id = _index_by(cases, key="name", label="case")
    business_by_id = _index_by(
        business_outcome_records, key="interaction_id", label="business outcome"
    )
    pilot_by_id = _index_by(
        pilot_evidence_records, key="interaction_id", label="pilot evidence"
    )

    records = []
    seen: set[str] = set()

    for execution_record in execution_records:
        interaction_id = execution_record["interaction_id"]
        if interaction_id in seen:
            raise ValueError(
                f"Duplicate execution interaction_id: {interaction_id!r}"
            )
        seen.add(interaction_id)

        case = case_by_id.get(interaction_id)
        business_outcome_record = business_by_id.get(interaction_id)
        pilot_evidence_record = pilot_by_id.get(interaction_id)
        if case is None:
            raise ValueError(f"No case for interaction: {interaction_id!r}")
        if business_outcome_record is None:
            raise ValueError(
                f"No business outcome for interaction: {interaction_id!r}"
            )
        if pilot_evidence_record is None:
            raise ValueError(
                f"No pilot evidence for interaction: {interaction_id!r}"
            )

        records.append(
            _consolidate_interaction(
                run_id=run_id,
                workload_id=workload_id,
                interaction_id=interaction_id,
                case=case,
                execution_record=execution_record,
                business_outcome_record=business_outcome_record,
                pilot_evidence_record=pilot_evidence_record,
            )
            | {"run_mode": run_mode}
        )

    # A completed run package requires exact identity coverage across all four
    # collections; any mismatch (including a dataset case with no execution
    # record) fails loudly.
    for label, index in (
        ("case", case_by_id),
        ("business outcome", business_by_id),
        ("pilot evidence", pilot_by_id),
    ):
        extra = set(index) - seen
        if extra:
            raise ValueError(
                f"{label} identities have no execution record: {sorted(extra)}"
            )

    return records


def build_run_summary(
    *,
    run_id: str,
    workload_id: str,
    execution_economics: dict,
    modeled_business_economics: dict,
    economic_value: dict,
    incremental_economics: dict,
    value_resilience: dict,
    workload_assessment: dict,
    decision_gates: dict,
    portfolio_action: dict,
    run_mode: str = "regression",
    simulation: dict | None = None,
) -> dict:
    """Assemble the run-level summary, preserving each section's exact values."""

    return {
        "run_id": run_id,
        "workload_id": workload_id,
        "run_mode": run_mode,
        "simulation": simulation,
        "execution_economics": execution_economics,
        "modeled_business_economics": modeled_business_economics,
        "economic_value": economic_value,
        "incremental_economics": incremental_economics,
        "value_resilience": value_resilience,
        "workload_assessment": workload_assessment,
        "decision_gates": decision_gates,
        "portfolio_action": portfolio_action,
    }


def run_dir(run_id: str, base: Path = RUNS_DIR) -> Path:
    """Return the deterministic ``runs/<run_id>`` directory for a run."""
    return base / run_id


def persist_run_package(
    run_id: str,
    interaction_records: list[dict],
    summary: dict,
    *,
    base: Path = RUNS_DIR,
) -> tuple[Path, Path]:
    """Create ``runs/<run_id>/`` and write ``interactions.jsonl`` + ``summary.json``."""

    directory = run_dir(run_id, base)
    directory.mkdir(parents=True, exist_ok=True)

    interactions_path = directory / "interactions.jsonl"
    summary_path = directory / "summary.json"

    with interactions_path.open("w", encoding="utf-8") as output_file:
        for record in interaction_records:
            output_file.write(json.dumps(record) + "\n")

    with summary_path.open("w", encoding="utf-8") as output_file:
        json.dump(summary, output_file, indent=2)
        output_file.write("\n")

    return interactions_path, summary_path
