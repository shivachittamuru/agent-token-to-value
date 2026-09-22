"""Read-only loader for run evidence packages under ``runs/<run_id>/``.

Presentation layers (e.g. the Value-to-Action dashboard) use this to load
``summary.json`` and ``interactions.jsonl`` without any agent, Azure, Foundry,
evaluator, or simulation dependency. This module contains no economic or
decision logic — it only discovers, loads, and validates run packages, and
tolerates older packages that lack newer optional fields.
"""

from __future__ import annotations

import json
from pathlib import Path

RUNS_DIR = Path("runs")


class RunPackageError(ValueError):
    """Raised when a selected run package is missing or structurally invalid."""


def discover_run_ids(base: Path | str = RUNS_DIR) -> list[str]:
    """Return valid run IDs (dirs with both package files), chronologically."""

    base_path = Path(base)
    if not base_path.exists():
        return []

    run_ids = [
        child.name
        for child in base_path.iterdir()
        if child.is_dir()
        and (child / "summary.json").is_file()
        and (child / "interactions.jsonl").is_file()
    ]
    # Run IDs are timestamp strings (or commit SHAs); lexical sort == chrono.
    return sorted(run_ids)


def latest_run_id(base: Path | str = RUNS_DIR) -> str | None:
    run_ids = discover_run_ids(base)
    return run_ids[-1] if run_ids else None


def load_summary(run_id: str, base: Path | str = RUNS_DIR) -> dict:
    path = Path(base) / run_id / "summary.json"
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise RunPackageError(f"summary.json not found for run {run_id!r}") from exc
    except json.JSONDecodeError as exc:
        raise RunPackageError(
            f"summary.json is not valid JSON for run {run_id!r}: {exc}"
        ) from exc

    if not isinstance(data, dict) or "run_id" not in data:
        raise RunPackageError(
            f"summary.json is structurally invalid for run {run_id!r}"
        )
    return data


def load_interactions(run_id: str, base: Path | str = RUNS_DIR) -> list[dict]:
    path = Path(base) / run_id / "interactions.jsonl"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RunPackageError(
            f"interactions.jsonl not found for run {run_id!r}"
        ) from exc

    records = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RunPackageError(
                f"interactions.jsonl line {line_number} is invalid JSON "
                f"for run {run_id!r}: {exc}"
            ) from exc
    return records


def load_run(run_id: str, base: Path | str = RUNS_DIR) -> dict:
    """Load one run package as ``{run_id, summary, interactions}``."""

    return {
        "run_id": run_id,
        "summary": load_summary(run_id, base),
        "interactions": load_interactions(run_id, base),
    }


def load_latest_run(base: Path | str = RUNS_DIR) -> dict | None:
    run_id = latest_run_id(base)
    return load_run(run_id, base) if run_id is not None else None
