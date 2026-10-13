"""Manual Azure billing evidence and deterministic workload cost allocation.

Runtime cost includes the resource's Foundry/model billing. It must not be
added to projected inference cost, which remains a separate modeled lens.
No Azure APIs or SDKs are used here.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from math import fsum, isfinite
from pathlib import Path

import yaml


def load_azure_runtime_cost_config(path: Path) -> dict:
    """Load and validate manual billing evidence, raising on invalid input."""
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    summarize_azure_runtime_cost(config)
    return config


def summarize_azure_runtime_cost(config: dict) -> dict:
    """Allocate selected resource charges over an inclusive billing period."""
    config = _mapping(config, "config")
    workload_id = _text(_required(config, "workload_id"), "workload_id")
    period, period_days = _period(_required(config, "period"))
    source = _source(_required(config, "source"))
    resources = _required(config, "resources")
    if not isinstance(resources, list) or not resources:
        raise ValueError("resources must be a non-empty list of billing evidence")

    names: set[str] = set()
    resource_allocations = []
    estimated_allocation = False
    for index, resource in enumerate(resources):
        label = f"resources[{index}]"
        resource = _mapping(resource, label)
        name = _text(_required(resource, "name"), f"{label}.name")
        if name in names:
            raise ValueError(f"duplicate resource name: {name}")
        names.add(name)
        service = _text(_required(resource, "service"), f"{name}.service")
        actual_cost = _nonnegative_number(
            _required(resource, "actual_cost_usd"), f"{name}.actual_cost_usd"
        )
        allocation = _mapping(_required(resource, "allocation"), f"{name}.allocation")
        method = _required(allocation, "method")
        if method not in ("direct", "fixed_percentage"):
            raise ValueError(f"{name}.allocation.method is unsupported: {method}")
        percentage = _nonnegative_number(
            _required(allocation, "percentage"), f"{name}.allocation.percentage"
        )
        if percentage > 1:
            raise ValueError(f"{name}.allocation.percentage must be between 0 and 1")
        if method == "direct" and percentage != 1:
            raise ValueError(f"{name}: direct allocation requires percentage 1.0")

        record = {
            "name": name,
            "service": service,
            "actual_cost_usd": actual_cost,
            "allocation_percentage": percentage,
            "allocated_cost_usd": actual_cost * percentage,
            "allocation_method": method,
        }
        for field in ("basis", "confidence"):
            if method == "fixed_percentage" or field in allocation:
                record[f"allocation_{field}"] = _text(
                    _required(allocation, field), f"{name}.allocation.{field}"
                )
        for field in ("reason", "note"):
            if field in allocation:
                record[f"allocation_{field}"] = _text(
                    allocation[field], f"{name}.allocation.{field}"
                )
            if field in resource:
                record[field] = _text(resource[field], f"{name}.{field}")
        resource_allocations.append(record)
        estimated_allocation |= method == "fixed_percentage" and actual_cost > 0

    selected_cost = fsum(
        record["actual_cost_usd"] for record in resource_allocations
    )
    allocated_cost = fsum(
        record["allocated_cost_usd"] for record in resource_allocations
    )
    return {
        "workload_id": workload_id,
        "cost_period": period,
        "period_days": period_days,
        "actual_selected_resource_cost_usd": selected_cost,
        "allocated_azure_runtime_cost_usd": allocated_cost,
        "allocated_azure_runtime_cost_per_day_usd": allocated_cost / period_days,
        "allocation_status": (
            "partially_allocated" if estimated_allocation else "directly_allocated"
        ),
        "cost_source": source,
        "resource_allocations": resource_allocations,
    }


def apply_azure_runtime_cost_to_modeled_economics(
    *,
    modeled_business_economics: dict,
    azure_runtime_cost: dict,
) -> dict:
    """Return a separate modeled runtime lens without mutating either input.

    ``azure_runtime_cost`` is a summary from ``summarize_azure_runtime_cost``.
    The caller must select a monthly scenario matching the billing period.
    Zero cost follows the inference lens's infinite-multiple convention.
    """
    business = _mapping(modeled_business_economics, "modeled_business_economics")
    runtime = _mapping(azure_runtime_cost, "azure_runtime_cost")
    contribution = _nonnegative_number(
        _required(business, "recovered_contribution_per_month"),
        "recovered_contribution_per_month",
    )
    cost = _nonnegative_number(
        _required(runtime, "allocated_azure_runtime_cost_usd"),
        "allocated_azure_runtime_cost_usd",
    )
    period, _ = _period(_required(runtime, "cost_period"))
    source = _source(_required(runtime, "cost_source"))
    status = _required(runtime, "allocation_status")
    if status not in ("partially_allocated", "directly_allocated"):
        raise ValueError(f"unsupported allocation_status: {status}")
    return {
        "modeled_recovered_contribution_usd": contribution,
        "allocated_azure_runtime_cost_usd": cost,
        "modeled_contribution_after_azure_runtime_usd": contribution - cost,
        "modeled_azure_runtime_value_multiple": (
            contribution / cost if cost > 0 else float("inf")
        ),
        "cost_period": period,
        "cost_source": source,
        "allocation_status": status,
    }


def _required(mapping: dict, field: str) -> object:
    if field not in mapping:
        raise ValueError(f"missing required field: {field}")
    return mapping[field]


def _mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _nonnegative_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number >= 0")
    number = float(value)
    if not isfinite(number) or number < 0:
        raise ValueError(f"{label} must be a finite number >= 0")
    return number


def _date(value: object, label: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{label} must be an ISO date (YYYY-MM-DD)") from error
        if parsed.isoformat() == value:
            return parsed
    raise ValueError(f"{label} must be an ISO date (YYYY-MM-DD)")


def _period(value: object) -> tuple[dict, int]:
    period = _mapping(value, "period")
    start = _date(_required(period, "start"), "period.start")
    end = _date(_required(period, "end"), "period.end")
    if end < start:
        raise ValueError("period.end must be >= period.start")
    currency = _text(_required(period, "currency"), "period.currency")
    if currency != "USD":
        raise ValueError("period.currency must be USD for *_usd cost fields")
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "currency": currency,
    }, (end - start).days + 1


def _source(value: object) -> dict:
    source = _mapping(value, "source")
    expected = {
        "type": "azure_cost_management_manual",
        "cost_basis": "actual_cost",
        "evidence_status": "observed_billing",
    }
    for field, expected_value in expected.items():
        if _required(source, field) != expected_value:
            raise ValueError(f"source.{field} must be {expected_value}")
    return deepcopy(source)
