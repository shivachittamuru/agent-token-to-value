---
title: Contoso Business Economics
description: Assumptions and economic boundaries for the Contoso Coffee demand-recovery scenario.
---

## Business question

Can AI economically recover customer demand the business cannot currently
serve? The Contoso agent answers menu inquiries; a response is not an order,
and an order after AI is not necessarily caused by AI.

## Modeled funnel

```text
Missed demand
× AI-eligible share
× measured successful-response rate
× assumed conversion
× average order value
× contribution margin
= modeled recovered contribution
```

Monthly inference cost is the cost per interaction multiplied by AI-addressable
interactions and the scenario horizon. See
[`economics/business_assumptions.yaml`](../economics/business_assumptions.yaml)
for the current inputs.

## Evidence status

| Measured | Assumed | Unknown until a real pilot |
|---|---|---|
| AI behavior and quality | Missed demand | Real incremental conversion |
| Token usage and inference cost | AI eligibility | Incremental contribution |
| Accepted Work | Conversion and order value | Customer economics |
| Cost per accepted outcome | Contribution margin | Causal attribution |

Simulation can demonstrate the evidence flow, but synthetic outcomes remain
simulation-scoped and do not establish production value.

## Economic lenses

* **Inference-only:** Modeled AI Value Multiple equals modeled recovered
  contribution divided by projected model inference cost.
* **System-adjusted:** Modeled Azure Runtime Value Multiple uses allocated
  Azure runtime cost. This is a separate denominator and must not be summed
  with inference cost without evidence they do not overlap.
* **Customer economics:** Customer Net Economic Value requires attributable
  incremental value less Total Relevant Customer Cost. The current evidence
  does not establish it.

The two modeled multiples are opportunity-sizing metrics, not realized ROI.
See the [Token-to-Value ladder](token_to_value_ladder.md),
[Azure runtime cost guide](azure_runtime_cost.md), and
[Value-to-Action framework](value-to-action/README.md).
