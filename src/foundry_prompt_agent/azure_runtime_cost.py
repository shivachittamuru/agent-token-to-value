"""Azure billing evidence and deterministic workload cost allocation.

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
    config = load_azure_runtime_allocation_config(path)
    config = build_azure_runtime_cost_config(
        allocation_config=config,
        cost_evidence=_mapping(_required(config, "manual_evidence"), "manual_evidence"),
    )
    summarize_azure_runtime_cost(config)
    return config


def load_azure_runtime_allocation_config(path: Path) -> dict:
    """Load resource identity/allocation rules without selecting billing evidence."""
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    validate_azure_runtime_allocation_config(config)
    return config


def validate_azure_runtime_allocation_config(config: dict) -> None:
    """Validate the shared allocation contract independently of actual costs."""
    _allocation_records(config)


def missing_azure_resource_cost_evidence(resource: dict) -> dict:
    """Describe absence from a billing query, not absence of all economic cost."""
    expectation = _billing_expectation(resource)
    billed_elsewhere = expectation == "may_be_billed_elsewhere"
    return {
        "billing_expectation": expectation,
        "actual_cost_usd": 0.0 if billed_elsewhere else None,
        "cost_evidence_status": (
            "no_direct_charge_returned" if billed_elsewhere else "not_returned"
        ),
    }


def build_azure_runtime_cost_config(
    *, allocation_config: dict, cost_evidence: dict
) -> dict:
    """Attach manual or automated evidence to rules, without allocating costs.

    Missing required direct charges prevent downstream summarization. Optional
    direct charges may be absent from an API query, without implying free service.
    """
    validate_azure_runtime_allocation_config(allocation_config)
    evidence = _mapping(cost_evidence, "cost_evidence")
    _period(_required(evidence, "period"))
    _source(_required(evidence, "source"))
    is_api_evidence = evidence["source"]["type"] == "azure_cost_management_api"
    observations = _required(evidence, "resources")
    if not isinstance(observations, list):
        raise ValueError("cost_evidence.resources must be a list")
    allowed = {resource["name"]: resource for resource in allocation_config["resources"]}
    by_name = {}
    for observation in observations:
        observation = _mapping(observation, "cost observation")
        name = _text(_required(observation, "name"), "cost observation.name")
        if name not in allowed:
            raise ValueError(f"cost evidence resource is not allow-listed: {name}")
        if name in by_name:
            raise ValueError(f"duplicate resource name in cost evidence: {name}")
        if (
            "billing_expectation" in observation
            and observation["billing_expectation"] != allowed[name]["billing_expectation"]
        ):
            raise ValueError(f"{name}: cost evidence billing_expectation mismatch")
        if "resource_id" in observation:
            resource_id = _text(observation["resource_id"], f"{name}.resource_id")
            configured_id = _text(
                _required(allowed[name], "resource_id"), f"{name}.resource_id"
            )
            if resource_id.casefold() != configured_id.casefold():
                raise ValueError(f"cost evidence resource_id mismatch: {name}")
        status = observation.get("cost_evidence_status", "observed_billing")
        if status == "observed_billing":
            _nonnegative_number(
                _required(observation, "actual_cost_usd"), f"{name}.actual_cost_usd"
            )
        elif status == "not_returned":
            if observation.get("actual_cost_usd") is not None:
                raise ValueError(f"{name}: not_returned cannot have an actual cost")
            if is_api_evidence:
                observation = {
                    **observation,
                    **missing_azure_resource_cost_evidence(allowed[name]),
                }
        elif status == "no_direct_charge_returned":
            _validate_no_direct_charge(allowed[name], observation)
        else:
            raise ValueError(f"{name}: unsupported cost_evidence_status: {status}")
        by_name[name] = observation

    result = deepcopy(allocation_config)
    result.pop("manual_evidence", None)
    result["period"] = deepcopy(evidence["period"])
    result["source"] = deepcopy(evidence["source"])
    for resource in result["resources"]:
        # Never carry stale manual observations into a different evidence period.
        resource.pop("actual_cost_usd", None)
        resource.pop("cost_evidence_status", None)
        observation = by_name.get(resource["name"])
        if observation is None:
            if is_api_evidence:
                resource.update(missing_azure_resource_cost_evidence(resource))
            else:
                resource["actual_cost_usd"] = None
                resource["cost_evidence_status"] = "not_returned"
        else:
            for field in ("actual_cost_usd", "cost_evidence_status", "note"):
                if field in observation:
                    resource[field] = deepcopy(observation[field])
    return result


def _allocation_records(config: dict) -> list[dict]:
    config = _mapping(config, "config")
    _text(_required(config, "workload_id"), "workload_id")
    resources = _required(config, "resources")
    if not isinstance(resources, list) or not resources:
        raise ValueError("resources must be a non-empty resource allow-list")

    names: set[str] = set()
    resource_allocations = []
    for index, resource in enumerate(resources):
        label = f"resources[{index}]"
        resource = _mapping(resource, label)
        name = _text(_required(resource, "name"), f"{label}.name")
        if name in names:
            raise ValueError(f"duplicate resource name: {name}")
        names.add(name)
        service = _text(_required(resource, "service"), f"{name}.service")
        expectation = _billing_expectation(resource)
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
            "billing_expectation": expectation,
            "allocation_percentage": percentage,
            "allocation_method": method,
        }
        if "resource_id" in resource:
            record["resource_id"] = _text(resource["resource_id"], f"{name}.resource_id")
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
    return resource_allocations


def summarize_azure_runtime_cost(config: dict) -> dict:
    """Allocate direct charges; reject missing required billing evidence."""
    resource_allocations = _allocation_records(config)
    period, period_days = _period(_required(config, "period"))
    source = _source(_required(config, "source"))
    estimated_allocation = False
    for record, resource in zip(resource_allocations, config["resources"], strict=True):
        name = record["name"]
        status = resource.get("cost_evidence_status", "observed_billing")
        if status == "no_direct_charge_returned":
            _validate_no_direct_charge(resource, resource)
        elif status != "observed_billing":
            raise ValueError(f"{name}: missing billing evidence ({status}); cannot allocate")
        actual_cost = _nonnegative_number(
            _required(resource, "actual_cost_usd"), f"{name}.actual_cost_usd"
        )
        record["actual_cost_usd"] = actual_cost
        record["allocated_cost_usd"] = actual_cost * record["allocation_percentage"]
        if "cost_evidence_status" in resource:
            record["cost_evidence_status"] = status
        method = record["allocation_method"]
        estimated_allocation |= method == "fixed_percentage" and actual_cost > 0

    selected_cost = fsum(
        record["actual_cost_usd"] for record in resource_allocations
    )
    allocated_cost = fsum(
        record["allocated_cost_usd"] for record in resource_allocations
    )
    return {
        "workload_id": config["workload_id"],
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


def _billing_expectation(resource: dict) -> str:
    expectation = _text(_required(resource, "billing_expectation"), "billing_expectation")
    if expectation not in ("direct_charge_expected", "may_be_billed_elsewhere"):
        raise ValueError(f"unsupported billing_expectation: {expectation}")
    return expectation


def _validate_no_direct_charge(resource: dict, observation: dict) -> None:
    name = resource["name"]
    if resource["billing_expectation"] != "may_be_billed_elsewhere":
        raise ValueError(f"{name}: no_direct_charge_returned requires may_be_billed_elsewhere")
    cost = _nonnegative_number(
        _required(observation, "actual_cost_usd"), f"{name}.actual_cost_usd"
    )
    if cost != 0:
        raise ValueError(f"{name}: no_direct_charge_returned requires zero direct charge")


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
    if _required(source, "type") not in (
        "azure_cost_management_manual", "azure_cost_management_api"
    ):
        raise ValueError("source.type must identify manual or API Cost Management evidence")
    expected = {
        "cost_basis": "actual_cost",
        "evidence_status": "observed_billing",
    }
    for field, expected_value in expected.items():
        if _required(source, field) != expected_value:
            raise ValueError(f"source.{field} must be {expected_value}")
    return deepcopy(source)
