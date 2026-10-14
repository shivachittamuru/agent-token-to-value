"""Normalize FOCUS Cost and Usage rows into workload cost evidence.

This module is provider-independent and performs no allocation or Azure calls.
"""

from __future__ import annotations

import calendar
import csv
from datetime import date, datetime
from math import fsum, isfinite
from pathlib import Path
from typing import Iterable

from foundry_prompt_agent.azure_runtime_cost import (
    validate_azure_runtime_allocation_config,
    validate_completed_calendar_month,
)

_COST_COLUMNS = {
    "effective_cost": "EffectiveCost",
    "billed_cost": "BilledCost",
}
_REQUIRED_COLUMNS = {
    "ResourceId",
    "BillingCurrency",
    "BillingPeriodStart",
    "BillingPeriodEnd",
}


def load_focus_cost_data(
    path: Path, *, cost_metric: str = "effective_cost"
) -> list[dict]:
    """Load a FOCUS-shaped CSV, ignoring documented leading comment lines."""
    metric_column = _cost_column(cost_metric)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        content = "".join(
            line for line in file if not line.lstrip().startswith("#")
        )
    reader = csv.DictReader(content.splitlines())
    fieldnames = reader.fieldnames
    if fieldnames is None:
        raise ValueError("FOCUS CSV requires a header row")
    if len(set(fieldnames)) != len(fieldnames):
        raise ValueError("FOCUS CSV has duplicate columns")
    missing = (_REQUIRED_COLUMNS | {metric_column}) - set(fieldnames)
    if missing:
        raise ValueError(
            "FOCUS CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )
    return [dict(row) for row in reader]


def month_period(month: str) -> tuple[date, date]:
    """Parse a YYYY-MM selector into its inclusive calendar-month bounds."""
    if not isinstance(month, str) or len(month) != 7 or month[4] != "-":
        raise ValueError("month must be YYYY-MM")
    try:
        start = date.fromisoformat(f"{month}-01")
    except ValueError as error:
        raise ValueError("month must be a valid YYYY-MM") from error
    if start.strftime("%Y-%m") != month:
        raise ValueError("month must be a valid YYYY-MM")
    end = date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
    return start, end


def normalize_focus_resource_costs(
    *,
    rows: Iterable[dict],
    allocation_config: dict,
    start: date,
    end: date,
    cost_metric: str = "effective_cost",
    focus_version: str = "1.2",
    today: date | None = None,
) -> dict:
    """Aggregate selected FOCUS rows into the shared resource-evidence shape."""
    metric_column = _cost_column(cost_metric)
    validate_completed_calendar_month(start=start, end=end, today=today)
    validate_azure_runtime_allocation_config(allocation_config)

    allowed: dict[str, dict] = {}
    for resource in allocation_config["resources"]:
        resource_id = resource.get("resource_id")
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise ValueError(f"{resource['name']}: full resource_id is required")
        key = resource_id.casefold()
        if key in allowed:
            raise ValueError(f"duplicate resource_id in allow-list: {resource_id}")
        allowed[key] = resource

    if not isinstance(focus_version, str) or not focus_version.strip():
        raise ValueError("focus_version must be a non-empty string")

    amounts: dict[str, list[float]] = {key: [] for key in allowed}
    included_currencies: set[str] = set()
    required_columns = _REQUIRED_COLUMNS | {metric_column}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"FOCUS row {index + 1} must be a mapping")
        missing = required_columns - row.keys()
        if missing:
            raise ValueError(
                f"FOCUS row {index + 1} is missing required fields: "
                + ", ".join(sorted(missing))
            )
        resource_id = row["ResourceId"]
        if resource_id is None or not str(resource_id).strip():
            continue
        key = str(resource_id).strip().casefold()
        if key not in allowed:
            continue

        row_start = _billing_date(row["BillingPeriodStart"], "BillingPeriodStart")
        row_end = _billing_date(row["BillingPeriodEnd"], "BillingPeriodEnd")
        if row_end < start or row_start > end:
            continue
        if row_start != start or row_end != end:
            raise ValueError(
                f"FOCUS row {index + 1} overlaps the requested month but does not "
                "represent the complete billing period"
            )

        currency = row["BillingCurrency"]
        if not isinstance(currency, str) or not currency.strip():
            raise ValueError(f"FOCUS row {index + 1} requires BillingCurrency")
        currency = currency.strip().upper()
        included_currencies.add(currency)
        if currency != "USD":
            raise ValueError("only USD FOCUS billing currency is supported")
        amount = _cost_number(row[metric_column], metric_column, index + 1)
        amounts[key].append(amount)

    if len(included_currencies) > 1:
        raise ValueError("FOCUS rows contain mixed billing currencies")

    resources = []
    for key, resource in allowed.items():
        resource_rows = amounts[key]
        if resource_rows:
            total = fsum(resource_rows)
            if total < 0:
                raise ValueError(
                    f"{resource['name']}: aggregated FOCUS cost must be nonnegative"
                )
            resources.append(
                {
                    "name": resource["name"],
                    "resource_id": resource["resource_id"],
                    "billing_expectation": resource["billing_expectation"],
                    "actual_cost_usd": total,
                    "cost_evidence_status": "observed_billing",
                }
            )
        elif resource["billing_expectation"] == "may_be_billed_elsewhere":
            resources.append(
                {
                    "name": resource["name"],
                    "resource_id": resource["resource_id"],
                    "billing_expectation": resource["billing_expectation"],
                    "actual_cost_usd": 0.0,
                    "cost_evidence_status": "no_direct_charge_returned",
                }
            )
        else:
            resources.append(
                {
                    "name": resource["name"],
                    "resource_id": resource["resource_id"],
                    "billing_expectation": resource["billing_expectation"],
                    "actual_cost_usd": None,
                    "cost_evidence_status": "not_returned",
                }
            )

    return {
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "currency": "USD",
        },
        "source": {
            "type": "focus_cost_and_usage",
            "focus_version": focus_version,
            "cost_metric": cost_metric,
            "cost_basis": cost_metric,
            "evidence_status": "observed_billing",
        },
        "resources": resources,
    }


def _cost_column(cost_metric: str) -> str:
    try:
        return _COST_COLUMNS[cost_metric]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "cost_metric must be 'effective_cost' or 'billed_cost'"
        ) from error


def _billing_date(value: object, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"FOCUS {field} must be an ISO date or timestamp")
    text = value.strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError as error:
            raise ValueError(
                f"FOCUS {field} must be an ISO date or timestamp"
            ) from error


def _cost_number(value: object, column: str, row_number: int) -> float:
    if isinstance(value, bool):
        raise ValueError(f"FOCUS row {row_number} {column} must be a finite number")
    try:
        amount = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"FOCUS row {row_number} {column} must be a finite number"
        ) from error
    if not isfinite(amount):
        raise ValueError(f"FOCUS row {row_number} {column} must be finite")
    return amount
