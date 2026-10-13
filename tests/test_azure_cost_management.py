from copy import deepcopy
from datetime import date
import importlib.util
from pathlib import Path
import sys

from azure.core.exceptions import AzureError
import pytest

from foundry_prompt_agent import azure_cost_management as costs
from foundry_prompt_agent.azure_runtime_cost import (
    apply_azure_runtime_cost_to_modeled_economics,
    build_azure_runtime_cost_config,
    load_azure_runtime_allocation_config,
    load_azure_runtime_cost_config,
    summarize_azure_runtime_cost,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "economics" / "azure_runtime_cost.yaml"
START = date(2026, 9, 1)
END = date(2026, 9, 30)
TODAY = date(2026, 10, 13)


@pytest.fixture(autouse=True)
def forbid_live_azure(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unit tests must not construct live Azure credentials or clients")

    monkeypatch.setattr(costs, "DefaultAzureCredential", forbidden)
    monkeypatch.setattr(costs, "PipelineClient", forbidden)


@pytest.fixture
def config():
    return load_azure_runtime_allocation_config(CONFIG_PATH)


def page(rows):
    return {
        "properties": {
            "columns": [
                {"name": "PreTaxCost", "type": "Number"},
                {"name": "ResourceId", "type": "String"},
                {"name": "Currency", "type": "String"},
            ],
            "rows": rows,
            "nextLink": None,
        }
    }


@pytest.fixture
def billing_page(config):
    amounts = [241.92, 4.12, 0.02, 0.0]
    return page([
        [amount, resource["resource_id"], "USD"]
        for resource, amount in zip(config["resources"], amounts, strict=True)
    ])


class FakeAdapter:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def query(self, *, scope, definition):
        self.calls.append((scope, deepcopy(definition)))
        return iter(self.pages)


def fetch(config, pages):
    return costs.fetch_azure_resource_costs(
        allocation_config=config,
        start=START,
        end=END,
        today=TODAY,
        adapter=FakeAdapter(pages),
    )


@pytest.mark.parametrize(
    ("start", "end"),
    [(START, END), (date(2024, 2, 1), date(2024, 2, 29)), (date(2026, 2, 1), date(2026, 2, 28))],
)
def test_valid_completed_calendar_month(start, end):
    costs.validate_completed_calendar_month(start=start, end=end, today=TODAY)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (START, date(2026, 9, 15)),
        (date(2026, 9, 2), END),
        (START, date(2026, 10, 31)),
        (END, START),
        (date(2026, 10, 1), date(2026, 10, 31)),
        (date(2026, 11, 1), date(2026, 11, 30)),
        ("2026-09-01", END),
    ],
)
def test_invalid_period_rejected_before_azure(config, start, end):
    with pytest.raises(ValueError):
        costs.fetch_azure_resource_costs(
            allocation_config=config, start=start, end=end, today=TODAY
        )


def test_previous_month_valid_on_first_day():
    costs.validate_completed_calendar_month(
        start=START, end=END, today=date(2026, 10, 1)
    )
    with pytest.raises(ValueError, match="completed"):
        costs.validate_completed_calendar_month(
            start=START, end=END, today=date(2026, 9, 30)
        )


@pytest.mark.parametrize("month", ["2026-9", "2026-09-01", "2026-13", "0000-01", "garbage"])
def test_invalid_month_selector(month):
    with pytest.raises(ValueError):
        costs.calendar_month(month)


def test_month_selector():
    assert costs.calendar_month("2026-09") == (START, END)


def test_query_is_subscription_actual_cost_with_explicit_allow_list(config, billing_page):
    adapter = FakeAdapter([billing_page])
    before = deepcopy(config)
    evidence = costs.fetch_azure_resource_costs(
        allocation_config=config, start=START, end=END, today=TODAY, adapter=adapter
    )
    scope, query = adapter.calls[0]
    assert scope == f"/subscriptions/{config['subscription_id']}"
    assert query["type"] == "ActualCost"
    assert query["timeframe"] == "Custom"
    assert query["timePeriod"] == {
        "from": "2026-09-01T00:00:00Z", "to": "2026-09-30T23:59:59Z"
    }
    assert query["dataset"]["grouping"] == [{"type": "Dimension", "name": "ResourceId"}]
    assert query["dataset"]["aggregation"] == {
        "totalCost": {"name": "PreTaxCost", "function": "Sum"}
    }
    assert query["dataset"]["filter"] == {
        "dimensions": {
            "name": "ResourceId", "operator": "In",
            "values": [resource["resource_id"] for resource in config["resources"]],
        }
    }
    assert evidence["period"]["currency"] == "USD"
    assert evidence["source"]["type"] == "azure_cost_management_api"
    assert config == before
    assert all("allocated_cost_usd" not in resource for resource in evidence["resources"])


def test_unrelated_resources_ignored_even_with_matching_name(config, billing_page):
    unrelated_id = config["resources"][0]["resource_id"].replace(
        "/resourceGroups/CognitiveGroup/", "/resourceGroups/not-allowed/"
    )
    billing_page["properties"]["rows"].append([1000, unrelated_id, "EUR"])
    assert len(fetch(config, [billing_page])["resources"]) == 4
    result = summarize_azure_runtime_cost(build_azure_runtime_cost_config(
        allocation_config=config, cost_evidence=fetch(config, [billing_page])
    ))
    assert result["actual_selected_resource_cost_usd"] == pytest.approx(246.06)


def test_returned_zero_is_observed(config, billing_page):
    evidence = fetch(config, [billing_page])
    zero = evidence["resources"][3]
    assert zero["actual_cost_usd"] == 0
    assert zero["cost_evidence_status"] == "observed_billing"


def test_missing_resource_stays_missing_and_allocator_refuses_total(config, billing_page):
    billing_page["properties"]["rows"].pop(2)
    evidence = fetch(config, [billing_page])
    missing = evidence["resources"][2]
    assert missing["actual_cost_usd"] is None
    assert missing["cost_evidence_status"] == "not_returned"
    assert missing["billing_expectation"] == "direct_charge_expected"
    combined = build_azure_runtime_cost_config(
        allocation_config=config, cost_evidence=evidence
    )
    assert combined["resources"][2]["actual_cost_usd"] is None
    with pytest.raises(ValueError, match="missing billing evidence.*not_returned"):
        summarize_azure_runtime_cost(combined)


def test_empty_response_is_not_observed_zero(config):
    evidence = fetch(config, [page([])])
    assert all(resource["cost_evidence_status"] == "not_returned" for resource in evidence["resources"][:3])
    assert evidence["resources"][3]["cost_evidence_status"] == "no_direct_charge_returned"
    with pytest.raises(ValueError, match="missing billing evidence"):
        summarize_azure_runtime_cost(build_azure_runtime_cost_config(
            allocation_config=config, cost_evidence=evidence
        ))


def test_live_style_september_without_appinsights_can_allocate(config, billing_page):
    billing_page["properties"]["rows"].pop()
    billing_page["properties"]["rows"][1][0] = 4.123483
    billing_page["properties"]["rows"][2][0] = 0.018399
    evidence = fetch(config, [billing_page])
    appinsights = evidence["resources"][3]
    assert appinsights["billing_expectation"] == "may_be_billed_elsewhere"
    assert appinsights["actual_cost_usd"] == 0
    assert appinsights["cost_evidence_status"] == "no_direct_charge_returned"
    summary = summarize_azure_runtime_cost(build_azure_runtime_cost_config(
        allocation_config=config, cost_evidence=evidence
    ))
    assert summary["actual_selected_resource_cost_usd"] == pytest.approx(246.061882)
    assert summary["allocated_azure_runtime_cost_usd"] == pytest.approx(52.525882)
    assert summary["allocation_status"] == "partially_allocated"
    allocation = summary["resource_allocations"][3]
    assert allocation["allocated_cost_usd"] == 0
    assert allocation["billing_expectation"] == "may_be_billed_elsewhere"
    assert allocation["cost_evidence_status"] == "no_direct_charge_returned"
    assert allocation["cost_evidence_status"] != "observed_billing"


@pytest.mark.parametrize("explicit_missing", [False, True])
def test_api_attachment_applies_billing_expectation(config, billing_page, explicit_missing):
    evidence = fetch(config, [billing_page])
    if explicit_missing:
        evidence["resources"][3]["actual_cost_usd"] = None
        evidence["resources"][3]["cost_evidence_status"] = "not_returned"
    else:
        evidence["resources"].pop()
    before = deepcopy(evidence)
    combined = build_azure_runtime_cost_config(allocation_config=config, cost_evidence=evidence)
    assert evidence == before
    assert combined["resources"][3]["actual_cost_usd"] == 0
    assert combined["resources"][3]["cost_evidence_status"] == "no_direct_charge_returned"
    assert summarize_azure_runtime_cost(combined)["allocated_azure_runtime_cost_usd"] == pytest.approx(52.524)


@pytest.mark.parametrize("expectation", ["unknown", None])
def test_unknown_billing_expectation_rejected_before_azure(config, expectation):
    config["resources"][0]["billing_expectation"] = expectation
    with pytest.raises(ValueError, match="billing_expectation"):
        costs.fetch_azure_resource_costs(
            allocation_config=config, start=START, end=END, today=TODAY
        )


def test_missing_billing_expectation_rejected_before_azure(config):
    del config["resources"][3]["billing_expectation"]
    with pytest.raises(ValueError, match="missing required field: billing_expectation"):
        costs.fetch_azure_resource_costs(
            allocation_config=config, start=START, end=END, today=TODAY
        )


@pytest.mark.parametrize("problem", ["direct_resource", "nonzero", "expectation_mismatch"])
def test_invalid_no_direct_charge_evidence_rejected(config, billing_page, problem):
    evidence = fetch(config, [billing_page])
    index = 0 if problem == "direct_resource" else 3
    observation = evidence["resources"][index]
    observation["cost_evidence_status"] = "no_direct_charge_returned"
    observation["actual_cost_usd"] = 1 if problem == "nonzero" else 0
    if problem == "expectation_mismatch":
        observation["billing_expectation"] = "direct_charge_expected"
    with pytest.raises(ValueError):
        build_azure_runtime_cost_config(allocation_config=config, cost_evidence=evidence)


def test_manual_appinsights_evidence_is_preserved():
    manual = load_azure_runtime_cost_config(CONFIG_PATH)
    appinsights = manual["resources"][3]
    assert appinsights["actual_cost_usd"] == 0
    assert appinsights.get("cost_evidence_status", "observed_billing") == "observed_billing"
    assert appinsights["note"] == (
        "No direct September cost line item. Telemetry cost may be attributed "
        "through the linked Log Analytics workspace."
    )
    summary = summarize_azure_runtime_cost(manual)
    assert summary["actual_selected_resource_cost_usd"] == pytest.approx(246.06)
    assert summary["allocated_azure_runtime_cost_usd"] == pytest.approx(52.524)


def test_resource_ids_match_case_insensitively(config, billing_page):
    for row in billing_page["properties"]["rows"]:
        row[1] = row[1].lower()
    evidence = fetch(config, [billing_page])
    assert evidence["resources"][0]["actual_cost_usd"] == pytest.approx(241.92)


def test_pages_and_column_order_are_normalized(config, billing_page):
    first = page(billing_page["properties"]["rows"][:2])
    second = page(billing_page["properties"]["rows"][2:])
    second["properties"]["columns"].reverse()
    for row in second["properties"]["rows"]:
        row.reverse()
    evidence = fetch(config, [first, second])
    assert [resource["actual_cost_usd"] for resource in evidence["resources"]] == [
        241.92, 4.12, 0.02, 0
    ]


@pytest.mark.parametrize("across_pages", [False, True])
def test_duplicate_resource_records_rejected(config, billing_page, across_pages):
    duplicate = deepcopy(billing_page["properties"]["rows"][0])
    duplicate[1] = duplicate[1].upper()
    pages = [billing_page]
    if across_pages:
        pages.append(page([duplicate]))
    else:
        billing_page["properties"]["rows"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate resource cost record"):
        fetch(config, pages)


@pytest.mark.parametrize("currency", ["EUR", "", None])
def test_currency_validation(config, billing_page, currency):
    billing_page["properties"]["rows"][0][2] = currency
    with pytest.raises(ValueError, match="only USD"):
        fetch(config, [billing_page])


@pytest.mark.parametrize("amount", [-1, float("nan"), float("inf"), True, "241.92"])
def test_invalid_api_amount(config, billing_page, amount):
    billing_page["properties"]["rows"][0][0] = amount
    with pytest.raises(ValueError, match="actual cost must be finite"):
        fetch(config, [billing_page])


@pytest.mark.parametrize("invalid", [{}, {"properties": {}}, page([[1]]), page([[1, None, "USD"]])])
def test_malformed_api_response(config, invalid):
    with pytest.raises(ValueError, match="Cost Management"):
        fetch(config, [invalid])


def test_missing_currency_column_is_rejected(config):
    invalid = page([])
    invalid["properties"]["columns"].pop()
    with pytest.raises(ValueError, match="requires ResourceId, PreTaxCost, Currency"):
        fetch(config, [invalid])


@pytest.mark.parametrize("problem", ["missing_subscription", "missing_id", "wrong_subscription", "wrong_name", "duplicate_id"])
def test_invalid_allow_list_rejected_before_azure(config, problem):
    if problem == "missing_subscription":
        del config["subscription_id"]
    elif problem == "missing_id":
        del config["resources"][0]["resource_id"]
    elif problem == "wrong_subscription":
        config["subscription_id"] = "00000000-0000-0000-0000-000000000000"
    elif problem == "wrong_name":
        config["resources"][0]["resource_id"] += "-wrong"
    else:
        duplicate = deepcopy(config["resources"][0])
        duplicate["name"] = duplicate["name"].upper()
        config["resources"].append(duplicate)
    with pytest.raises(ValueError):
        costs.fetch_azure_resource_costs(
            allocation_config=config, start=START, end=END, today=TODAY
        )


def test_both_evidence_paths_use_the_same_allocation(config, billing_page):
    manual = summarize_azure_runtime_cost(load_azure_runtime_cost_config(CONFIG_PATH))
    evidence = fetch(config, [billing_page])
    combined = build_azure_runtime_cost_config(
        allocation_config=config, cost_evidence=evidence
    )
    automated = summarize_azure_runtime_cost(combined)
    for summary in (manual, automated):
        assert summary["actual_selected_resource_cost_usd"] == pytest.approx(246.06)
        assert summary["allocated_azure_runtime_cost_usd"] == pytest.approx(52.524)
        assert summary["resource_allocations"][0]["allocation_percentage"] == 0.20
        assert summary["allocation_status"] == "partially_allocated"
    config["resources"][0]["allocation"]["percentage"] = 0.5
    adjusted = summarize_azure_runtime_cost(build_azure_runtime_cost_config(
        allocation_config=config, cost_evidence=evidence
    ))
    assert adjusted["allocated_azure_runtime_cost_usd"] == pytest.approx(241.92 * 0.5 + 4.14)
    assert evidence["resources"][0]["actual_cost_usd"] == 241.92
    runtime_lens = apply_azure_runtime_cost_to_modeled_economics(
        modeled_business_economics={"recovered_contribution_per_month": 1701, "ai_value_multiple": 123},
        azure_runtime_cost=automated,
    )
    assert runtime_lens["modeled_azure_runtime_value_multiple"] == pytest.approx(1701 / 52.524)


def test_allocation_config_does_not_contain_actual_costs(config):
    assert all("actual_cost_usd" not in resource for resource in config["resources"])
    assert config["manual_evidence"]["resources"][0]["actual_cost_usd"] == 241.92


def test_evidence_builder_does_not_fall_back_to_manual_cost(config):
    evidence = deepcopy(config["manual_evidence"])
    evidence["resources"].pop()
    combined = build_azure_runtime_cost_config(allocation_config=config, cost_evidence=evidence)
    assert combined["resources"][-1]["cost_evidence_status"] == "not_returned"
    assert combined["resources"][-1]["actual_cost_usd"] is None
    assert "manual_evidence" not in combined


@pytest.mark.parametrize("problem", ["duplicate", "unrelated", "wrong_id", "missing_with_cost"])
def test_invalid_evidence_merge(config, billing_page, problem):
    evidence = fetch(config, [billing_page])
    if problem == "duplicate":
        evidence["resources"].append(deepcopy(evidence["resources"][0]))
    elif problem == "unrelated":
        evidence["resources"][0]["name"] = "not-allowed"
    elif problem == "wrong_id":
        evidence["resources"][0]["resource_id"] += "-wrong"
    else:
        evidence["resources"][0]["cost_evidence_status"] = "not_returned"
    with pytest.raises(ValueError):
        build_azure_runtime_cost_config(allocation_config=config, cost_evidence=evidence)


def install_fake_rest(monkeypatch, pages, error=None):
    requests = []
    responses = []
    credentials = []

    class FakeCredential:
        def __init__(self):
            credentials.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload
            self.closed = False

        def raise_for_status(self):
            if error is not None:
                raise error

        def json(self):
            return self.payload

        def close(self):
            self.closed = True

    class FakeClient:
        @classmethod
        def __class_getitem__(cls, key):
            return cls

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def send_request(self, request, **kwargs):
            requests.append(request)
            response = FakeResponse(pages[len(requests) - 1])
            responses.append(response)
            return response

    monkeypatch.setattr(costs, "DefaultAzureCredential", FakeCredential)
    monkeypatch.setattr(costs, "PipelineClient", FakeClient)
    return requests, responses, credentials


def test_rest_adapter_posts_and_follows_next_link(monkeypatch, config):
    scope = f"/subscriptions/{config['subscription_id']}"
    next_link = f"{costs.ARM_ENDPOINT}{scope}/providers/Microsoft.CostManagement/Query?api-version=2025-03-01&$skiptoken=next"
    first = page([])
    first["properties"]["nextLink"] = next_link
    requests, responses, credentials = install_fake_rest(monkeypatch, [first, page([])])
    adapter = costs.AzureCostManagementAdapter()
    assert not credentials
    assert len(list(adapter.query(scope=scope, definition={"type": "ActualCost"}))) == 2
    assert len(credentials) == 1
    assert all(request.method == "POST" for request in requests)
    assert requests[1].url == next_link
    assert requests[0].content == requests[1].content
    assert all(response.closed for response in responses)


@pytest.mark.parametrize("next_link", [
    "https://example.com/query", "http://management.azure.com/query",
    "https://management.azure.com/subscriptions/other/providers/Microsoft.CostManagement/query",
])
def test_rest_adapter_rejects_out_of_scope_pagination(monkeypatch, config, next_link):
    first = page([])
    first["properties"]["nextLink"] = next_link
    requests, _, _ = install_fake_rest(monkeypatch, [first])
    with pytest.raises(ValueError, match="nextLink left the query scope"):
        list(costs.AzureCostManagementAdapter().query(
            scope=f"/subscriptions/{config['subscription_id']}", definition={}
        ))
    assert len(requests) == 1


def test_rest_adapter_rejects_pagination_loop(monkeypatch, config):
    scope = f"/subscriptions/{config['subscription_id']}"
    first = page([])
    first["properties"]["nextLink"] = f"{costs.ARM_ENDPOINT}{scope}/providers/Microsoft.CostManagement/query?api-version={costs.API_VERSION}"
    requests, _, _ = install_fake_rest(monkeypatch, [first])
    with pytest.raises(ValueError, match="repeated a nextLink"):
        list(costs.AzureCostManagementAdapter().query(scope=scope, definition={}))
    assert len(requests) == 1


def test_rest_adapter_surfaces_azure_error_and_closes_response(monkeypatch, config):
    _, responses, _ = install_fake_rest(monkeypatch, [page([])], error=AzureError("forbidden"))
    with pytest.raises(AzureError, match="forbidden"):
        list(costs.AzureCostManagementAdapter().query(
            scope=f"/subscriptions/{config['subscription_id']}", definition={}
        ))
    assert responses[0].closed


@pytest.mark.parametrize("missing", [None, "direct", "elsewhere"])
def test_cli_prints_costs_without_writing_fixture(monkeypatch, capsys, config, billing_page, missing):
    spec = importlib.util.spec_from_file_location(
        "fetch_cost_cli", ROOT / "scripts" / "fetch_azure_runtime_cost.py"
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    if missing is not None:
        billing_page["properties"]["rows"].pop(2 if missing == "direct" else 3)
    evidence = fetch(config, [billing_page])
    monkeypatch.setattr(cli, "fetch_azure_resource_costs", lambda **kwargs: evidence)
    monkeypatch.setattr(sys, "argv", ["fetch_cost_cli", "--month", "2026-09"])
    before = CONFIG_PATH.read_bytes()
    assert cli.main() == (1 if missing == "direct" else 0)
    output = capsys.readouterr()
    assert CONFIG_PATH.read_bytes() == before
    if missing == "direct":
        assert "not_returned (not observed zero)" in output.out
        assert "missing billing evidence" in output.err
        assert "Raw selected-resource total" not in output.out
    else:
        assert "Raw selected-resource total: 246.060000 USD" in output.out
        assert "Allocated Azure runtime cost: 52.524000 USD" in output.out
        assert not output.err
        if missing == "elsewhere":
            assert "0.000000 USD [no_direct_charge_returned; charges may be billed elsewhere]" in output.out
