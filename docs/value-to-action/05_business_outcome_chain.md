# Business Outcome Chain — v1

## Decision Question

What observable business changes must occur after Accepted Work before we can claim that the AI workload created business value?

## Core Distinction

Accepted Work is evidence that the AI system performed its assigned task correctly.

It is not yet evidence that the business outcome occurred.

```text
Accepted Work
      ≠
Business Outcome
      ≠
Economic Value
```

Each transition requires its own evidence.

## Contoso Outcome Chain

```text
Customer Inquiry
      ↓
AI Interaction Attempted
      ↓
Accepted Work
      ↓
Customer Intent Preserved
      ↓
Order Completed
      ↓
Incremental Order Recovered
      ↓
Recovered Revenue
      ↓
Recovered Contribution
```

## Outcome Levels

| Level | Question | Contoso Example |
|---|---|---|
| System Output | Did the AI produce acceptable work? | Accepted menu response |
| Workflow Outcome | Did the customer journey advance? | Customer remained engaged instead of abandoning |
| Business Outcome | Did a business event occur? | Order completed |
| Incremental Business Outcome | Did AI cause an outcome that otherwise would not have occurred? | Otherwise-lost order recovered |
| Economic Value | What is that incremental outcome worth? | Incremental contribution |

## Why Incrementality Matters

Observed orders are not automatically AI-created value.

```text
Order after AI interaction
        ≠
Order caused by AI interaction
```

Some customers may have ordered anyway through another channel or after waiting for staff.

The relevant business outcome is therefore not simply:

```text
orders after AI
```

but:

```text
incremental orders attributable to AI
```

## Current Contoso Evidence

### Measured

- attempted AI interactions,
- Accepted Work,
- execution consumption,
- model cost,
- tool usage,
- latency.

### Modeled / Assumed

- missed contacts per day,
- AI-eligible rate,
- conversion rate,
- average order value,
- contribution margin.

### Not Yet Proven

- actual unanswered-demand baseline,
- whether an Accepted Work interaction preserves customer intent,
- whether the customer subsequently places an order,
- whether that order would otherwise have been lost,
- incremental orders attributable to AI,
- realized recovered revenue,
- realized recovered contribution.

## Current Business-Economics Funnel

The current implementation models:

```text
Missed Contacts
      ×
AI-Eligible Rate
      ↓
Addressable Contacts
      ×
AI Success Rate
      ↓
Successful Contacts
      ×
Assumed Conversion Rate
      ↓
Modeled Recovered Orders
      ×
Average Order Value
      ↓
Modeled Recovered Revenue
      ×
Contribution Margin
      ↓
Modeled Recovered Contribution
```

This is a scenario model.

It should not be interpreted as observed business performance.

## Important Naming Rule

Use language that matches the evidence.

Prefer:

- **modeled recovered orders**
- **modeled recovered contribution**
- **observed orders after AI interaction**
- **incremental orders**, only when incrementality is evidenced

Avoid calling modeled outcomes "realized" or "recovered" without qualification.

## Evidence Needed to Prove the Chain

A real-world pilot should establish linkage between:

```text
Interaction ID
      ↓
Accepted Work
      ↓
Customer / session outcome
      ↓
Order event
      ↓
Economic outcome
```

At minimum, evidence should make it possible to determine:

1. whether an eligible customer interaction occurred,
2. whether the interaction became Accepted Work,
3. whether the customer continued toward purchase,
4. whether an order was completed,
5. whether that outcome was plausibly incremental,
6. what economic value was associated with the outcome.

## Counterfactual Requirement

Incremental value requires comparison against what would likely have happened without the AI capability.

Possible evidence approaches include:

- control or holdout groups,
- phased rollout,
- matched historical baseline,
- comparable staff-unavailable periods,
- other defensible experimental or quasi-experimental designs.

The stronger the value claim, the stronger the counterfactual evidence should be.

## Current Boundary

Today we can confidently say:

```text
AI Consumption
      ↓
Accepted Work
```

We cannot yet confidently say:

```text
Accepted Work
      ↓
Incremental Order
      ↓
Recovered Contribution
```

Those links remain business hypotheses.

## Key Takeaways

- Accepted Work is necessary but not sufficient for business value.
- Workflow outcomes, business outcomes, and economic value are different layers.
- An observed downstream event is not automatically incremental.
- Incremental value requires a counterfactual.
- Business assumptions should remain visibly separate from measured outcomes.
- Every arrow in the value chain requires evidence proportional to the strength of the claim.
- The purpose of a pilot is not merely to demonstrate that the AI works; it is to reduce uncertainty in the links between Accepted Work and business value.

## Next Step

Define the minimum Business Outcome Evidence Record needed to connect an AI interaction to downstream workflow and order outcomes without prematurely claiming causality.