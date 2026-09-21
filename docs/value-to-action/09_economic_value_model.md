# Economic Value Model — v1

## Decision Question

How should proven or modeled business outcomes be translated into economic value without overstating what the available evidence supports?

## Core Distinction

A business outcome is not automatically economic value.

```text
Business Outcome
      ↓
Economic Translation
      ↓
Economic Value
```

For Contoso:

```text
Incremental Order
      ×
Order Value
      ×
Contribution Margin
      ↓
Incremental Contribution
```

## Value Must Be Incremental

The relevant value is the economic difference caused by the workload relative to its counterfactual.

```text
Value with AI
-
Value without AI
=
Incremental Economic Value
```

Do not value all treatment-arm activity as AI-created value.

## Three Economic Layers

Keep these layers separate.

### 1. Modeled Economic Value

Uses scenario assumptions to estimate potential value.

```text
Assumed Missed Demand
      ×
Assumed Eligibility
      ×
Technical Success
      ×
Assumed Conversion
      ×
Assumed Order Value
      ×
Assumed Contribution Margin
      ↓
Modeled Recovered Contribution
```

Useful for:

- exploration,
- sensitivity analysis,
- deciding whether a pilot is worth running.

It is not realized ROI.

### 2. Evidence-Backed Incremental Value

Uses observed business outcomes and a defensible counterfactual.

```text
Treatment Outcome
-
Counterfactual Outcome
      ↓
Incremental Outcome

Incremental Outcome
      ×
Observed Unit Economics
      ↓
Incremental Economic Value
```

Useful for evaluating whether the workload actually created value.

### 3. Customer Net Economic Value

Economic value must ultimately be compared with the relevant cost of producing it.

```text
Customer Net Economic Value
=
Incremental Economic Value
-
Total Relevant Customer Cost
```

This is broader than model inference economics.

## Current Contoso Metric

The existing Token-to-Value implementation calculates:

```text
Modeled Recovered Contribution
──────────────────────────────
Measured Model Inference Cost
=
Modeled AI Value Multiple
```

This metric remains useful.

It answers:

> If the business assumptions are approximately correct, how large is the modeled contribution opportunity relative to model inference cost?

It does not answer:

> Has the AI workload produced proven customer ROI?

## Why the Existing Metric Must Be Preserved

The original metric represents an earlier evidence stage.

```text
Scenario Economics
      ↓
Pilot Economics
      ↓
Evidence-Backed Economics
```

Later evidence should refine the economic model rather than erase the earlier scenario model.

## Current Evidence State

### Measured

- AI execution evidence,
- Accepted Work,
- model inference cost,
- known direct execution cost.

### Measured but Economically Incomplete

- Azure AI Search activity,
- broader execution cost.

### Assumed

- missed contacts,
- AI eligibility,
- conversion,
- average order value,
- contribution margin.

### Unknown

- realized business outcomes,
- treatment/control conversion,
- incremental conversion lift,
- incremental orders,
- realized incremental contribution,
- full execution cost,
- total customer cost.

## Economic Evidence Status

Every economic result should carry an evidence status.

Examples:

```text
MODELED
```

The value is derived materially from assumptions.

```text
OBSERVED
```

The underlying business event was directly measured.

```text
INCREMENTAL
```

A defensible counterfactual supports attribution to the workload.

```text
PARTIAL_COST
```

Economic value may be known, but relevant cost attribution remains incomplete.

These states should not be silently collapsed into one number.

## Value Numerator

For Contoso, the preferred economic numerator is contribution rather than gross revenue.

```text
Incremental Orders
      ×
Observed Average Order Value
      ×
Contribution Margin
      ↓
Incremental Contribution
```

Revenue alone can overstate economic benefit because it ignores the cost of fulfilling the order.

## Cost Denominators

Different questions require different cost boundaries.

### Model Economics

```text
Incremental or Modeled Value
────────────────────────────
Model Inference Cost
```

### Execution Economics

```text
Incremental Value
────────────────────────
Full AI Execution Cost
```

### Customer Economics

```text
Incremental Economic Value
-
Total Relevant Customer Cost
=
Customer Net Economic Value
```

Do not label one of these as another.

## Average vs Incremental Economics

Historical average cost and the cost of serving additional demand may differ.

For investment decisions, ask:

```text
Additional Economic Value
-
Additional Cost Required
=
Incremental Net Economic Value
```

A workload may have attractive historical economics but poor economics for the next unit of scale.

## Current Economic Boundary

Today we can calculate:

```text
Modeled Economic Value
+
Measured Model Cost
+
Partial Direct Execution Cost
```

We cannot yet calculate:

```text
Realized Incremental Economic Value
```

or:

```text
Customer Net Economic Value
```

because business incrementality and total relevant cost are not yet established.

## Guardrails

- Do not call modeled contribution realized value.
- Do not value treatment-arm outcomes as incremental without a counterfactual.
- Prefer contribution over revenue when contribution is the economic objective.
- Do not treat partial execution cost as total customer cost.
- Do not convert Unknown economic inputs to zero.
- Preserve the evidence status of every value result.
- Keep scenario economics available even after stronger evidence becomes available.
- Use incremental economics when evaluating additional investment.

## Key Takeaways

- Business outcomes require an economic translation before becoming value.
- Economic value should be incremental to the counterfactual.
- Modeled value, observed value, and incremental value are different evidence states.
- The original AI Value Multiple is a valid scenario metric, not proven ROI.
- Contribution is usually more economically meaningful than gross revenue.
- Net Economic Value requires both attributable value and the relevant customer cost.
- A precise value number is not stronger than the evidence supporting its inputs.

## Next Step

Create an Economic Value Record that preserves modeled economics while refusing to claim realized incremental value or Customer Net Economic Value when the required evidence is Unknown.