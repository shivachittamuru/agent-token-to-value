---
title: Token-to-Value Ladder
description: A concise progression from AI consumption to verified work and economic value.
---

## The ladder

```text
Token Spend
    ↓ measure input, output, cached, and reasoning tokens
Token Cost
    ↓ apply model pricing
Token Efficiency
    ↓ cost and tokens per interaction
Token Effectiveness
    ↓ cost per successful or accepted outcome
Accepted Work
    ↓ count work only after task and required guardrails pass
System Economics
    ↓ compare modeled contribution with broader Azure runtime cost
Economic Value
    ↓ test attribution, Total Relevant Customer Cost, and the next investment
```

Each step adds evidence. A lower token count is not automatically better if
quality or accepted work falls.

## Keep the cost boundaries separate

| Lens | Formula | What it includes |
|---|---|---|
| Modeled AI Value Multiple | Modeled recovered contribution ÷ projected inference cost | Inference only |
| Modeled Azure Runtime Value Multiple | Modeled recovered contribution ÷ allocated Azure runtime cost | Azure services such as Search, model runtime, and observability |
| Customer Net Economic Value | Incremental attributable value − Total Relevant Customer Cost | Customer-wide economics, not yet established |

The Azure model-runtime charge already includes relevant Foundry/model
billing. Do not add the inference and Azure denominators without evidence that
they do not overlap. Neither modeled multiple is realized ROI.

## Evidence progression

Tokens, inference cost, technical quality, and Accepted Work can be measured
in evaluation runs. The Contoso model uses assumptions for missed demand,
eligibility, conversion, order value, and contribution margin. A real pilot is
needed to establish attributable outcomes and customer economics.

See [business economics](business_case_and_economics.md) for the Contoso
scenario, [Azure runtime cost](azure_runtime_cost.md) for cost-source
adapters, and [Value-to-Action](value-to-action/README.md) for decision gates.
