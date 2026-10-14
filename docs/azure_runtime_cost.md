---
title: Azure Runtime Cost
description: Cost-source adapters, resource allocation, and period-level snapshots for system economics.
---

## Why runtime cost matters

Inference cost alone can understate the cost of operating an AI system. The
project keeps these boundaries distinct:

```text
Model Cost → Azure Runtime Cost → Full Technical Execution Cost
                                      → Total Relevant Customer Cost
```

Azure runtime includes selected Azure services such as Search, Foundry/model
runtime, and observability. It does not establish full execution or customer
cost. Do not add its denominator to inference cost without evidence that the
charges do not overlap; the Foundry resource charge already includes relevant
model billing.

## Azure Cost Management path

```text
Cost Management API → explicit resource allow-list
                    → normalized cost evidence
                    → shared allocation
                    → period snapshot
                    → modeled system economics
```

The API adapter queries Actual Cost for one completed month, in USD, at
resource-level granularity. It uses only the full resource IDs configured in
[`economics/azure_runtime_cost.yaml`](../economics/azure_runtime_cost.yaml).
It does not discover resources by tag, group, or subscription-wide attribution.

Local retrieval is explicit and read-only unless snapshot saving is requested:

```powershell
uv run python scripts\fetch_azure_runtime_cost.py --month 2026-09
```

Live retrieval uses `DefaultAzureCredential`, including Azure CLI login, and
requires subscription-level Cost Management query access. No live query is
needed for tests or local FOCUS validation.

## Shared-resource allocation

Search is shared across workloads. With no historical per-index usage
evidence, the configured 20% engineering estimate allocates its cost to this
workload. Foundry/model runtime and Log Analytics are directly allocated.
Application Insights may be billed through Log Analytics.

The validated September reference is approximately **$246.06 raw selected
resource cost** and **$52.53 allocated workload runtime cost**. Its allocation
status is `partially_allocated`, not exact. These are period totals, not costs
caused by individual evaluation runs.

## FOCUS adapter

[`focus_cost.py`](../src/foundry_prompt_agent/focus_cost.py) reads a local CSV
subset of FOCUS 1.2 and normalizes it into the same resource evidence contract.

* The adapter consumes `ResourceId`, billing period, `BillingCurrency`, and
  the selected cost field. Null and non-allow-listed resource IDs are ignored.
* `EffectiveCost` is the default economic basis for ongoing spend analysis.
* `BilledCost` is available explicitly when an invoice-oriented basis is needed.
* The adapter uses the same resource allow-list and centralized allocation.
* FOCUS snapshots use the existing snapshot validator and load in both dashboards.
* The sample is derived from validated September evidence, not a fresh Azure
  export. Its equal EffectiveCost/BilledCost values are a fixture simplification.

The adapter pattern demonstrates source independence, not full multi-cloud
support or every FOCUS column.

Validate the checked-in sample without Azure:

```powershell
uv run python scripts\read_focus_runtime_cost.py --input focus_samples\contoso-september-2026.csv --month 2026-09 --cost-metric effective_cost
```

Add `--cost-metric billed_cost` to select the alternate basis or
`--save-snapshot` to write a separately named local snapshot.

## Evidence and snapshots

Both ingestion paths feed `build_azure_runtime_cost_config` and
`summarize_azure_runtime_cost` in
[`azure_runtime_cost.py`](../src/foundry_prompt_agent/azure_runtime_cost.py).
Allocation formulas therefore remain independent of the billing source.

`cost_snapshot.py` validates and persists monthly summaries with source
provenance and resource-level evidence. Missing expected direct charges remain
`not_returned` and block a complete allocation. An absent resource configured
as `may_be_billed_elsewhere` is represented as zero direct charge with
`no_direct_charge_returned`. This does not mean it has no economic cost
elsewhere.

Run evaluation or simulation with a prepared snapshot:

```powershell
uv run python scripts\run_evaluation.py --cost-snapshot cost_snapshots\contoso-demand-recovery-2026-09.json
```

The monthly snapshot is referenced as period-level operating-cost evidence;
the runner never divides it into a run cost. The dashboards display that same
snapshot without source-specific handling. Runtime-adjusted economics are
modeled because their numerator is modeled contribution. They are not realized
ROI, incremental economics, or Customer Net Economic Value.

## Key caveats

* Billing data can lag or change during reconciliation.
* Shared resources require an explicit allocation basis; estimates remain estimates.
* `EffectiveCost` and `BilledCost` are distinct bases and must not be silently substituted.
* A month-level runtime value multiple is not a per-run return.
* Azure runtime cost is broader than inference cost but narrower than Total Relevant Customer Cost.
