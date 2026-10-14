"""Local, period-level cost evidence persistence, independent of Azure APIs."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
from math import isclose, isfinite
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from foundry_prompt_agent.azure_runtime_cost import (
    summarize_azure_runtime_cost,
    validate_completed_calendar_month,
)

COST_SNAPSHOTS_DIR = Path("cost_snapshots")
_SUMMARY_FIELDS = (
    "workload_id",
    "cost_period",
    "period_days",
    "actual_selected_resource_cost_usd",
    "allocated_azure_runtime_cost_usd",
    "allocated_azure_runtime_cost_per_day_usd",
    "allocation_status",
    "resource_allocations",
)


def build_cost_snapshot(
    *, azure_runtime_cost: dict, snapshot_id: str | None = None
) -> dict:
    """Copy a validated runtime summary into a timestamped monthly snapshot."""
    snapshot = {
        field: deepcopy(_required(azure_runtime_cost, field))
        for field in _SUMMARY_FIELDS
    }
    snapshot["evidence_source"] = deepcopy(_required(azure_runtime_cost, "cost_source"))
    period = snapshot["cost_period"]
    start = _required(period, "start")
    if not isinstance(start, str):
        raise ValueError("cost_period.start must be an ISO date")
    snapshot["snapshot_id"] = (
        snapshot_id if snapshot_id is not None else f"{snapshot['workload_id']}-{start[:7]}"
    )
    snapshot["created_at"] = datetime.now(timezone.utc).isoformat()
    allocations = snapshot["resource_allocations"]
    if not isinstance(allocations, list):
        raise ValueError("resource_allocations must be a list")
    for resource in allocations:
        if not isinstance(resource, dict):
            raise ValueError("resource_allocations must contain mappings")
        if "cost_evidence_status" not in resource:
            # Legacy manual summaries identify observed billing at source level.
            if _required(snapshot["evidence_source"], "type") != "azure_cost_management_manual":
                raise ValueError("API resource evidence requires cost_evidence_status")
            resource["cost_evidence_status"] = "observed_billing"
    validate_cost_snapshot(snapshot)
    return snapshot


def validate_cost_snapshot(snapshot: dict) -> None:
    """Validate provenance, completed-month scope, and allocator consistency."""
    identity = _required(snapshot, "snapshot_id")
    if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", identity):
        raise ValueError("snapshot_id must be a non-empty filename-safe identifier")
    created_at = _required(snapshot, "created_at")
    if not isinstance(created_at, str):
        raise ValueError("created_at must be an ISO timestamp with timezone")
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError as error:
        raise ValueError("created_at must be an ISO timestamp with timezone") from error
    if created.tzinfo is None:
        raise ValueError("created_at must include a timezone")

    period = _required(snapshot, "cost_period")
    dates = []
    for field in ("start", "end"):
        value = _required(period, field)
        if not isinstance(value, str):
            raise ValueError(f"cost_period.{field} must be an ISO date")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"cost_period.{field} must be an ISO date") from error
        if parsed.isoformat() != value:
            raise ValueError(f"cost_period.{field} must be an ISO date")
        dates.append(parsed)
    validate_completed_calendar_month(start=dates[0], end=dates[1])
    validate_completed_calendar_month(
        start=dates[0], end=dates[1], today=created.astimezone(timezone.utc).date()
    )

    allocations = _required(snapshot, "resource_allocations")
    if not isinstance(allocations, list) or not allocations:
        raise ValueError("resource_allocations must be a non-empty list")
    resources = []
    for record in allocations:
        resource = {
            field: _required(record, field)
            for field in (
                "name", "service", "billing_expectation",
                "cost_evidence_status", "actual_cost_usd",
            )
        }
        resource["allocation"] = {
            "method": _required(record, "allocation_method"),
            "percentage": _required(record, "allocation_percentage"),
        }
        for field in ("basis", "confidence", "reason"):
            if f"allocation_{field}" in record:
                resource["allocation"][field] = record[f"allocation_{field}"]
        if "resource_id" in record:
            resource["resource_id"] = record["resource_id"]
        resources.append(resource)

    expected = summarize_azure_runtime_cost({
        "workload_id": _required(snapshot, "workload_id"),
        "period": period,
        "source": _required(snapshot, "evidence_source"),
        "resources": resources,
    })
    period_days = _required(snapshot, "period_days")
    if isinstance(period_days, bool) or not isinstance(period_days, int) or period_days != expected["period_days"]:
        raise ValueError("period_days does not match the cost period")
    if _required(snapshot, "allocation_status") != expected["allocation_status"]:
        raise ValueError("allocation_status does not match resource allocations")
    for field in (
        "actual_selected_resource_cost_usd", "allocated_azure_runtime_cost_usd",
        "allocated_azure_runtime_cost_per_day_usd",
    ):
        _matching_cost(_required(snapshot, field), expected[field], field)
    for record, calculated in zip(allocations, expected["resource_allocations"], strict=True):
        _matching_cost(
            _required(record, "allocated_cost_usd"),
            calculated["allocated_cost_usd"],
            f"{record['name']}.allocated_cost_usd",
        )
    try:
        json.dumps(snapshot, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("snapshot must contain finite JSON-serializable data") from error


def save_cost_snapshot(snapshot: dict, path: Path) -> None:
    """Validate then atomically write a full snapshot, never a partial file."""
    validate_cost_snapshot(snapshot)
    path.parent.mkdir(parents=True, exist_ok=True)
    output = NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
    )
    temporary_path = Path(output.name)
    try:
        with output:
            json.dump(snapshot, output, indent=2, sort_keys=True, allow_nan=False)
            output.write("\n")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_cost_snapshot(path: Path, *, workload_id: str | None = None) -> dict:
    """Read and validate local evidence; optionally require the run's workload."""
    with path.open("r", encoding="utf-8") as file:
        snapshot = json.load(file, object_pairs_hook=_unique_object)
    validate_cost_snapshot(snapshot)
    if workload_id is not None and snapshot["workload_id"] != workload_id:
        raise ValueError("cost snapshot workload_id does not match the run workload")
    return snapshot


def _required(record: object, field: str) -> object:
    if not isinstance(record, dict):
        raise ValueError("cost snapshot contract requires mappings")
    if field not in record:
        raise ValueError(f"missing required cost snapshot field: {field}")
    return record[field]


def _matching_cost(value: object, expected: float, field: str) -> None:
    if (
        isinstance(value, bool) or not isinstance(value, (int, float))
        or not isfinite(value) or value < 0
        or not isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12)
    ):
        raise ValueError(f"{field} must be finite, nonnegative, and match resource evidence")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate cost snapshot JSON field: {key}")
        result[key] = value
    return result
