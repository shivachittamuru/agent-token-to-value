"""Subscription Actual Cost ingestion; workload allocation stays in the allocator."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timezone
from math import isfinite
from typing import Iterable, Iterator, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from azure.core import PipelineClient
from azure.core.pipeline.policies import BearerTokenCredentialPolicy, RetryPolicy
from azure.core.rest import HttpRequest, HttpResponse
from azure.identity import DefaultAzureCredential

from foundry_prompt_agent.azure_runtime_cost import (
    missing_azure_resource_cost_evidence,
    validate_azure_runtime_allocation_config,
)

ARM_ENDPOINT = "https://management.azure.com"
API_VERSION = "2025-03-01"


class CostQueryAdapter(Protocol):
    """The only Azure boundary; fakes return the same JSON pages as the REST API."""

    def query(self, *, scope: str, definition: dict) -> Iterable[dict]: ...


class AzureCostManagementAdapter:
    """Authenticated, retried REST query with complete pagination."""

    def query(self, *, scope: str, definition: dict) -> Iterator[dict]:
        path = f"{scope}/providers/Microsoft.CostManagement/query"
        url = f"{ARM_ENDPOINT}{path}?api-version={API_VERSION}"
        seen: set[str] = set()
        with DefaultAzureCredential() as credential:
            with PipelineClient[HttpRequest, HttpResponse](
                ARM_ENDPOINT,
                policies=[
                    RetryPolicy(retry_total=3),
                    BearerTokenCredentialPolicy(
                        credential, f"{ARM_ENDPOINT}/.default"
                    ),
                ],
            ) as client:
                while url:
                    parsed = urlsplit(url)
                    if (
                        parsed.scheme != "https"
                        or parsed.netloc != "management.azure.com"
                        or parsed.path.casefold() != path.casefold()
                        or parsed.fragment
                    ):
                        raise ValueError("Cost Management nextLink left the query scope")
                    if url in seen:
                        raise ValueError("Cost Management pagination repeated a nextLink")
                    seen.add(url)
                    response = client.send_request(
                        HttpRequest("POST", url, json=definition),
                        connection_timeout=10,
                        read_timeout=60,
                    )
                    try:
                        response.raise_for_status()
                        payload = response.json()
                    finally:
                        response.close()
                    if not isinstance(payload, dict):
                        raise ValueError("Cost Management response must be a JSON object")
                    properties = payload.get("properties")
                    if not isinstance(properties, dict):
                        raise ValueError("Cost Management response is missing properties")
                    next_link = properties.get("nextLink")
                    if next_link is not None and (
                        not isinstance(next_link, str) or not next_link
                    ):
                        raise ValueError("Cost Management nextLink must be a URL or null")
                    yield payload
                    url = next_link


def validate_completed_calendar_month(
    *, start: date, end: date, today: date | None = None
) -> None:
    """Reject partial, current, and future months before authenticating."""
    for label, value in (("start", start), ("end", end)):
        if not isinstance(value, date) or isinstance(value, datetime):
            raise ValueError(f"{label} must be a date")
    last_day = calendar.monthrange(start.year, start.month)[1]
    if start.day != 1 or end != date(start.year, start.month, last_day):
        raise ValueError("only a complete calendar month is supported")
    current_date = today if today is not None else datetime.now(timezone.utc).date()
    if end >= current_date.replace(day=1):
        raise ValueError("only a completed calendar month is supported")


def calendar_month(month: str) -> tuple[date, date]:
    """Parse a YYYY-MM selector; completion is checked by the fetch operation."""
    if not isinstance(month, str) or not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("month must be YYYY-MM")
    start = date.fromisoformat(f"{month}-01")
    return start, date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])


def _allow_list(config: dict) -> tuple[str, dict[str, dict]]:
    validate_azure_runtime_allocation_config(config)
    subscription_id = config.get("subscription_id")
    if not isinstance(subscription_id, str):
        raise ValueError("subscription_id is required")
    try:
        subscription_id = str(UUID(subscription_id))
    except ValueError as error:
        raise ValueError("subscription_id must be a UUID") from error
    scope = f"/subscriptions/{subscription_id}"
    allowed: dict[str, dict] = {}
    for resource in config["resources"]:
        resource_id = resource.get("resource_id")
        if not isinstance(resource_id, str):
            raise ValueError(f"{resource['name']}: full resource_id is required")
        match = re.fullmatch(
            r"/subscriptions/([^/]+)/resourceGroups/([^/]+)/providers/([^/]+)/([^/]+)/([^/]+)",
            resource_id,
            re.IGNORECASE,
        )
        if (
            match is None
            or match[1].casefold() != subscription_id
            or match[5].casefold() != resource["name"].casefold()
        ):
            raise ValueError(f"{resource['name']}: invalid resource_id or wrong subscription")
        key = resource_id.casefold()
        if key in allowed:
            raise ValueError(f"duplicate resource_id: {resource_id}")
        allowed[key] = resource
    return scope, allowed


def fetch_azure_resource_costs(
    *,
    allocation_config: dict,
    start: date,
    end: date,
    adapter: CostQueryAdapter | None = None,
    today: date | None = None,
) -> dict:
    """Retrieve USD resource totals, retaining zero and distinguishing absence.

    No allocation is performed. Duplicate aggregate rows fail rather than risk
    double-counting. All pages must succeed before any evidence is returned.
    """
    validate_completed_calendar_month(start=start, end=end, today=today)
    scope, allowed = _allow_list(allocation_config)
    definition = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{end.isoformat()}T23:59:59Z",
        },
        "dataset": {
            "aggregation": {"totalCost": {"name": "PreTaxCost", "function": "Sum"}},
            "grouping": [{"type": "Dimension", "name": "ResourceId"}],
            "filter": {
                "dimensions": {
                    "name": "ResourceId",
                    "operator": "In",
                    "values": [resource["resource_id"] for resource in allowed.values()],
                }
            },
        },
    }
    query_adapter = adapter if adapter is not None else AzureCostManagementAdapter()
    costs: dict[str, float] = {}
    for page in query_adapter.query(scope=scope, definition=definition):
        if not isinstance(page, dict) or not isinstance(page.get("properties"), dict):
            raise ValueError("Cost Management response is missing properties")
        properties = page["properties"]
        columns = properties.get("columns")
        rows = properties.get("rows")
        if not isinstance(columns, list) or not isinstance(rows, list):
            raise ValueError("Cost Management response requires columns and rows")
        names = []
        for column in columns:
            if not isinstance(column, dict) or not isinstance(column.get("name"), str):
                raise ValueError("Cost Management column requires a name")
            names.append(column["name"])
        if len(set(names)) != len(names):
            raise ValueError("Cost Management response has duplicate columns")
        if not {"ResourceId", "PreTaxCost", "Currency"}.issubset(names):
            raise ValueError("Cost Management response requires ResourceId, PreTaxCost, Currency")
        for row in rows:
            if not isinstance(row, list) or len(row) != len(names):
                raise ValueError("Cost Management row does not match columns")
            values = dict(zip(names, row, strict=True))
            resource_id = values["ResourceId"]
            if not isinstance(resource_id, str):
                raise ValueError("Cost Management ResourceId must be a string")
            key = resource_id.casefold()
            if key not in allowed:
                continue
            if values["Currency"] != "USD":
                raise ValueError(f"{resource_id}: only USD billing currency is supported")
            if key in costs:
                raise ValueError(f"duplicate resource cost record: {resource_id}")
            amount = values["PreTaxCost"]
            if (
                isinstance(amount, bool)
                or not isinstance(amount, (int, float))
                or not isfinite(amount)
                or amount < 0
            ):
                raise ValueError(f"{resource_id}: actual cost must be finite and >= 0")
            costs[key] = float(amount)

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat(), "currency": "USD"},
        "source": {
            "type": "azure_cost_management_api",
            "cost_basis": "actual_cost",
            "scope": scope,
            "evidence_status": "observed_billing",
        },
        "resources": [
            {
                "name": resource["name"],
                "resource_id": resource["resource_id"],
                **(
                    {
                        "billing_expectation": resource["billing_expectation"],
                        "actual_cost_usd": costs[key],
                        "cost_evidence_status": "observed_billing",
                    }
                    if key in costs
                    else missing_azure_resource_cost_evidence(resource)
                ),
            }
            for key, resource in allowed.items()
        ],
    }
