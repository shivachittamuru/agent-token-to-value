---
title: Azure runtime cost evidence and allocation
description: Manual and automated monthly billing evidence feeding one allocation model.
---

## Evidence boundary

[azure_runtime_cost.yaml](../economics/azure_runtime_cost.yaml) separates the
subscription, full resource-ID allow-list, and allocation rules from the
`manual_evidence` block. That block retains manually validated Azure Cost
Management Actual Cost for September 1-30, 2026, in USD.
Only resources with billing evidence are selected. The Application Insights
zero-cost entry records no direct September line item; telemetry charges may
be attributed through the linked Log Analytics workspace.

The selected resource charges total $246.06. Search is shared, and historical
per-index query logs were unavailable. Its 20% engineering-estimate allocation
attributes $48.384 to the workload. Foundry/model runtime ($4.12) and Log
Analytics ($0.02) are directly allocated at 100%.

The workload-attributed total is $52.524, or $52.524 / 30 = $1.7508 per day.
Billing evidence remains `observed_billing`, while workload cost is
`partially_allocated`, not exact.

## Standalone API

[azure_runtime_cost.py](../src/foundry_prompt_agent/azure_runtime_cost.py) uses
local YAML and pure arithmetic, with no Azure SDK or API calls.

```python
from pathlib import Path

from foundry_prompt_agent.azure_runtime_cost import (
    apply_azure_runtime_cost_to_modeled_economics,
    load_azure_runtime_cost_config,
    summarize_azure_runtime_cost,
)

config = load_azure_runtime_cost_config(
    Path("economics") / "azure_runtime_cost.yaml"
)
runtime = summarize_azure_runtime_cost(config)
adjusted = apply_azure_runtime_cost_to_modeled_economics(
    modeled_business_economics=modeled_business_economics,
    azure_runtime_cost=runtime,
)
```

Loading and summarizing both validate the contract. Costs must be finite,
nonnegative numbers, and percentages must be within [0, 1]. Direct allocation
requires 1.0; fixed-percentage allocation requires a basis and confidence.
Missing fields, duplicate resource names, unsupported methods, invalid dates,
and non-USD currencies fail with `ValueError`. Periods include both endpoints.
Summary dates are ISO strings; raw YAML dates may be Python `date` values.

Each resource requires `billing_expectation`, either `direct_charge_expected`
or `may_be_billed_elsewhere`; unknown or missing values fail validation.

`load_azure_runtime_cost_config` still selects the September manual fixture.
For automated ingestion, use `load_azure_runtime_allocation_config`, then
`build_azure_runtime_cost_config` to attach new evidence to those same rules.
The builder never fills gaps using the checked-in manual fixture.

The summary preserves actual selected-resource cost, allocated workload cost,
source metadata, and individual allocations. A positive-cost resource using a
fixed percentage conservatively makes the summary `partially_allocated`;
all-direct evidence is `directly_allocated`. Neither status establishes
complete customer cost.

The economics helper accepts the summary and an already-computed business
scenario. It returns a separate record and does not mutate either input.
Select a monthly scenario aligned with the cost period; the helper does not
prorate the modeled numerator. Zero runtime cost returns an infinite multiple,
following the existing inference metric convention, even for a zero numerator.

## Automated completed-month ingestion

[azure_cost_management.py](../src/foundry_prompt_agent/azure_cost_management.py)
queries the configured subscription using the
[Cost Management Query API](https://learn.microsoft.com/en-us/rest/api/cost-management/query/usage?view=rest-cost-management-2025-03-01).
It uses `ActualCost`, a custom UTC calendar-month interval, a `ResourceId`
dimension filter containing only the four allowed IDs, and `Sum(PreTaxCost)`
grouped by `ResourceId`, without daily granularity. Billing currency must be
USD; there is no currency conversion, forecast, or amortized-cost path.

Only completed calendar months are accepted. Partial periods, the current
month, and future months fail before credentials or API calls. This protects
the monthly modeled numerator from comparison with partial-month cost.

The REST adapter uses `DefaultAzureCredential`, including your existing
Azure CLI login, with Azure Core's bearer-token and retry policies. It follows
every `nextLink` using the same POST body and rejects pagination loops or
links outside the original subscription query endpoint. Authentication,
permission, HTTP, and malformed-response errors are surfaced, not converted
to zero or partial totals.

Rows are decoded by column name, not position. Resource-ID matching is
case-insensitive, unrelated rows are ignored, and duplicate resource totals
within or across pages fail rather than risk double-counting.

Returned zero-cost rows have `actual_cost_usd: 0` and
`cost_evidence_status: observed_billing`, regardless of billing expectation.
Absent resources are handled according to their configured expectation:

* `direct_charge_expected`: Search, Foundry/model runtime, and Log Analytics
  remain `not_returned` with `actual_cost_usd: null`. Missing required direct
  charges prevent the allocator from producing a runtime-cost total.
* `may_be_billed_elsewhere`: Application Insights receives
  `actual_cost_usd: 0` and `cost_evidence_status: no_direct_charge_returned`.
  The allocator may continue, and the distinct status survives in its output.

`no_direct_charge_returned` means no direct charge was returned in this
billing query. It is not an observed zero billing row and does not mean the
resource has no economic cost anywhere. Its telemetry charges may be
attributed through Log Analytics. The status requires a configured
`may_be_billed_elsewhere` expectation and zero direct charge; it cannot be
used to bypass missing direct charges or hide a positive returned charge.

The attachment path uses the same absence rules for API evidence. It does
not infer an API-query absence from an omitted manual evidence entry, and it
never falls back to a manual amount. The preserved September manual
Application Insights zero and explanatory note are unchanged.

### Read-only live validation

Install the project dependencies with `uv sync`, then authenticate with
`az login` in the tenant containing the configured subscription. You need
subscription-level Cost Management read/query access, typically the
`Cost Management Reader` role, and any billing-account cost-visibility
settings required by your subscription agreement.
See [assign Cost Management access](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/assign-access-acm-data).

The implementation uses `azure-identity` and `azure-core`, not an additional
management SDK. The `CostQueryAdapter` protocol allows unit tests to use
fake response pages without constructing credentials or making Azure calls.

```powershell
uv run python scripts\fetch_azure_runtime_cost.py --month 2026-09
```

[fetch_azure_runtime_cost.py](../scripts/fetch_azure_runtime_cost.py) prints
each resource's evidence, then uses the existing allocator to print raw and
allocated totals. It writes no files and never updates the manual fixture or
run artifacts. Missing required direct charges are printed explicitly and
produce a nonzero exit status rather than a success-shaped total. An absent
Application Insights direct charge is printed with
`no_direct_charge_returned` and a warning that charges may be billed elsewhere.

September validation expectations are $246.06 raw selected-resource cost and
$52.524 allocated runtime cost. These remain regression expectations, not
production constants. With Application Insights absent, the September
live-style fixture uses $241.92 Search, $4.123483 Foundry/model runtime,
and $0.018399 Log Analytics. It produces approximately $246.061882 in selected
direct charges and $52.525882 allocated runtime cost, using the same 20%
Search allocation. This remains partially allocated technical runtime cost,
not complete customer cost.

### September live validation result

The read-only query on October 13, 2026 returned Search at $241.920000,
Foundry/model runtime at approximately $4.123483, and Log Analytics at
approximately $0.018399. These resource amounts match the manual fixture when
rounded to cents. Their observed-row subtotal is approximately $246.061882,
not a complete allow-list total.

Azure did not return Application Insights. Before Slice 1C.1, its evidence
remained `not_returned`, and the CLI exited with status 1 without producing an
allocated workload total. Slice 1C.1 now represents that query absence as
`no_direct_charge_returned`, allowing allocation under the explicit billing
expectation rather than asserting an observed zero. The live-style fixture
verifies approximately $52.525882 allocated; this is not a new live query.
The preserved manual path still reproduces $246.06 raw and $52.524 allocated.

## Two separate modeled lenses

* Modeled AI Value Multiple = modeled recovered contribution / projected inference cost
* Modeled Azure Runtime Value Multiple = modeled recovered contribution / allocated Azure runtime cost
* Modeled contribution after Azure runtime = modeled recovered contribution - allocated Azure runtime cost

Using the current business assumptions and the documented illustrative run
(90% success and $0.0074 per interaction), modeled recovered contribution is
$1,701/month. Projected inference cost is $13.32, giving an AI Value Multiple
of approximately 127.703x. The separate runtime lens gives $1,648.476 modeled
contribution after Azure runtime and approximately 32.385x runtime value.

Do not add the denominators: the Foundry resource's Azure charge already
includes relevant model billing. The existing AI Value Multiple formula and
[economic_value.py](../src/foundry_prompt_agent/economic_value.py) are unchanged.

Azure runtime cost includes Search and telemetry as well as Foundry/model
runtime, so it is broader than inference cost. Human effort, governance,
support, and other relevant customer costs remain outside this evidence
boundary. Runtime cost is therefore not Total Relevant Customer Cost and
does not establish complete customer-cost evidence.

The numerator remains modeled. These outputs do not establish realized
contribution, ROI, incremental economics, or Customer Net Economic Value.
No FinOps Toolkit integration, runner integration, simulation changes, run
artifact persistence, or dashboard changes are included.
