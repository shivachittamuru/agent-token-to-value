---
title: Manual Azure runtime cost allocation
description: September 2026 billing evidence and a separate modeled runtime economics lens.
---

## Evidence boundary

[azure_runtime_cost.yaml](../economics/azure_runtime_cost.yaml) records manually
validated Azure Cost Management Actual Cost for September 1-30, 2026, in USD.
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
No ingestion automation, FinOps Toolkit integration, runner integration, or
dashboard changes are included.
