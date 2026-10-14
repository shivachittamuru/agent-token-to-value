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
allocated totals. Without snapshot-saving flags it writes no files. It never
updates the manual fixture or run artifacts. Missing required direct charges are printed explicitly and
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

## Period-level snapshots and run packages

Azure billing data and agent execution operate on different clocks.
[cost_snapshot.py](../src/foundry_prompt_agent/cost_snapshot.py) persists an
already-prepared cost summary as local monthly evidence, without Azure SDK
imports or API calls. Both manual and automated summaries normalize into
the same snapshot contract, retaining source provenance.

The default snapshot ID is `workload_id-YYYY-MM`, for example
`contoso-demand-recovery-2026-09`, not a run ID. The default CLI save path is
`cost_snapshots/contoso-demand-recovery-2026-09.json`.

### Snapshot contract

| Field                                       | Meaning                                      |
|---------------------------------------------|----------------------------------------------|
| `snapshot_id`                               | Period-level, filename-safe evidence ID      |
| `workload_id`                               | Workload whose resource boundary was used    |
| `cost_period`                               | Inclusive start, end, and USD currency       |
| `period_days`                               | Number of days in the completed month        |
| `created_at`                                | Timezone-aware ISO creation timestamp        |
| `evidence_source`                           | Original manual or API source metadata       |
| `actual_selected_resource_cost_usd`         | Selected-resource direct charges             |
| `allocated_azure_runtime_cost_usd`           | Workload-attributed runtime cost              |
| `allocated_azure_runtime_cost_per_day_usd`   | Allocated monthly cost divided by days       |
| `allocation_status`                         | Direct or partially allocated status         |
| `resource_allocations`                      | Full resource-level evidence and allocations |

Resource records preserve name, service, resource ID when supplied,
`billing_expectation`, `cost_evidence_status`, actual charge, allocation
percentage, allocated cost, allocation method, and basis/confidence when
relevant. Notes and allocation reasons also survive. Manual summaries whose
resource status was implicit carry it explicitly as `observed_billing`;
API-query absence remains `no_direct_charge_returned`, never an observed zero.

Validation rejects partial or uncompleted months, missing provenance,
duplicate resources or JSON fields, non-finite amounts, inconsistent totals,
and invalid billing/allocation states. It reuses the existing allocator to
check arithmetic rather than introducing allocation formulas. Saves validate
first and atomically replace the destination; failed writes do not leave a
partial snapshot. Keep snapshots referenced by runs unchanged, and use a
different path for corrected evidence.

### Preparing evidence separately

Live retrieval is still an explicit preparation step:

```powershell
uv run python scripts\fetch_azure_runtime_cost.py --month 2026-09 --save-snapshot
uv run python scripts\fetch_azure_runtime_cost.py --month 2026-09 --snapshot-path cost_snapshots\september-reviewed.json
```

`--snapshot-path` also requests saving. With neither flag, the command remains
read-only. Missing required direct charges prevent snapshot creation.

The preserved manual fixture can be prepared without Azure connectivity:

```python
from pathlib import Path

from foundry_prompt_agent.azure_runtime_cost import (
    load_azure_runtime_cost_config,
    summarize_azure_runtime_cost,
)
from foundry_prompt_agent.cost_snapshot import build_cost_snapshot, save_cost_snapshot

runtime = summarize_azure_runtime_cost(
    load_azure_runtime_cost_config(Path("economics") / "azure_runtime_cost.yaml")
)
snapshot = build_cost_snapshot(azure_runtime_cost=runtime)
save_cost_snapshot(
    snapshot,
    Path("cost_snapshots") / f"{snapshot['snapshot_id']}.json",
)
```

### Optional runner input

Both runners load and validate local snapshots before executing agent cases:

```powershell
uv run python scripts\run_evaluation.py --cost-snapshot cost_snapshots\contoso-demand-recovery-2026-09.json
uv run python scripts\run_simulation.py --seed 42 --cost-snapshot cost_snapshots\contoso-demand-recovery-2026-09.json
```

[run_artifacts.py](../src/foundry_prompt_agent/run_artifacts.py) adds a compact
`azure_runtime_cost` section to the run's summary: snapshot ID, workload,
period, creation timestamp, source metadata, raw and allocated costs,
allocation status, and the input snapshot path when supplied. Full resource
allocations stay in the snapshot file. The API also accepts a loaded snapshot
dict without a path; prepare and retain its full snapshot separately.

The monthly bill is operating-cost evidence referenced by the run, not cost
caused by that run. No run-level Azure cost or cost-per-run claim is created.
Evaluation and simulation never retrieve live Cost Management data, and
runs without a snapshot retain the existing summary shape.

The runner passes the `days_per_month` it actually used for the modeled
contribution to the summary builder as `modeled_business_days_per_month`.
Runtime-adjusted modeled economics are added only when that explicit
projection horizon matches the validated snapshot's completed calendar-month
length and the modeled monthly contribution is available. The current 30-day
scenario is compatible with September's 30-day cost snapshot. A 12-day scenario
or a missing horizon is not; a 30-day scenario also does not silently become
a 31-day scenario for October billing.

Compatible runs persist a separate `azure_runtime_modeled_economics` section
and print `=== Azure Runtime Economics ===`. The existing helper computes the
runtime lens without adding inference cost to the Azure bill. Incompatible
runs retain `azure_runtime_cost`, omit runtime-adjusted economics, and print
an explanation. Nothing is invented or prorated. Runs without a snapshot
do not print the Azure Runtime Economics section.

Execution Economics continues to report run-level direct execution cost.
Its console now calls Search, observability, and human recovery
`Not attributed at run level`, and separately reports whether period-level
Azure evidence is available via a snapshot. A monthly bill is never divided
by evaluation interaction count or substituted for
`known_direct_execution_cost_usd`. Full Execution Cost remains unestablished.
AI Value Multiple, Customer Net Economic Value, and decision/action logic
remain unchanged.

Runtime cost still excludes human effort, governance, support, and other
relevant customer costs. Persisting it does not turn it into Total Relevant
Customer Cost or establish complete customer-cost evidence.

## Two separate modeled lenses

* Modeled AI Value Multiple = modeled recovered contribution / projected inference cost
* Modeled Azure Runtime Value Multiple = modeled recovered contribution / allocated Azure runtime cost
* Modeled contribution after Azure runtime = modeled recovered contribution - allocated Azure runtime cost

### Economic ladder example

For the current regression scenario, modeled recovered contribution is
$1,701/month and projected inference cost is approximately $11.07:

* Inference-only economics: Modeled AI Value Multiple is approximately 153.6x
* Broader Azure operating economics: Modeled Azure Runtime Value Multiple is approximately 32.4x against $52.525882 allocated runtime cost
* Complete customer economics: not yet established

The lower runtime multiple is expected: its denominator includes Search,
Foundry/model runtime, and observability rather than inference alone. It is a
second lens, not a replacement for the inference-only multiple. Modeled
contribution after allocated runtime cost is approximately $1,648.474118.
Both multiples still use the original modeled contribution as their numerator.

Human recovery, governance, support, and other relevant customer costs remain
outside the evidence boundary. These outputs establish neither Customer Net
Economic Value nor realized ROI or incremental economics.

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
No FinOps Toolkit integration or dashboard changes are included. Both runners
use the same optional local snapshot and monthly-basis guard; synthetic and
incremental economics are unchanged.
