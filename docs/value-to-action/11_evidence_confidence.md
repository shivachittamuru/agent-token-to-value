# Evidence Confidence — v1

## Decision Question

How strongly does the available evidence support the workload's current value claims?

## Core Rule

Economic attractiveness and evidence confidence are separate dimensions.

```text
Economic Value
        ≠
Evidence Confidence
```

A large modeled value does not become more credible merely because the number is large.

## Evidence Confidence Asks

For each important claim:

```text
What is being claimed?
        ↓
What evidence supports it?
        ↓
How directly was it observed?
        ↓
How representative is it?
        ↓
How much uncertainty remains?
```

## Claim-Level Confidence

Confidence should attach to specific claims rather than to the workload as one universal score.

Examples:

| Claim | Current Contoso Evidence |
|---|---|
| Model/token consumption | Measured |
| Accepted Work | Measured in regression evaluation |
| Search/tool activity | Measured |
| Full execution cost | Partial |
| Real eligible demand volume | Unknown |
| Customer conversion after AI | Unknown |
| Incremental conversion lift | Unknown |
| Incremental contribution | Unknown |
| Customer Net Economic Value | Unknown |
| Next-dollar economics | Unknown |

## Evidence Classes

Use a small descriptive vocabulary.

### Measured

Directly observed in the relevant system or evaluation.

### Modeled

Derived materially from assumptions or scenario inputs.

### Observed

A real downstream business event was observed, but causality may not be established.

### Incremental / Causal

A defensible counterfactual supports attribution to the workload.

### Unknown

The evidence required for the claim does not yet exist.

These labels describe evidence type, not whether the result is economically favorable.

## Confidence Dimensions

When a claim requires deeper assessment, consider:

### Directness

How directly was the thing being claimed measured?

```text
direct observation
>
proxy
>
assumption
```

### Representativeness

Does the evidence reflect the population and environment relevant to the decision?

A ten-case regression suite may provide strong technical evidence while providing weak evidence about production customer behavior.

### Sample Adequacy

Is there enough evidence to distinguish a real pattern from noise?

The required sample depends on the claim and decision.

### Counterfactual Strength

For causal value claims, how credible is the comparison against what would have happened without the workload?

### Completeness

Are materially important parts of the claim still Unknown?

Examples:

- incomplete execution cost,
- missing human intervention cost,
- missing business outcomes.

### Recency / Persistence

Does the evidence represent current and sustained behavior, or only a point-in-time result?

## Current Contoso Confidence Profile

### Stronger Evidence

```text
Technical execution
Accepted Work
Token consumption
Model cost
Tool-call activity
```

These are directly measured in the current regression environment.

### Partial Evidence

```text
Execution economics
```

Known direct model cost exists, but Search, observability, and human recovery remain economically incomplete.

### Modeled Evidence

```text
Recovered orders
Recovered contribution
AI Value Multiple
```

These depend materially on scenario assumptions.

### Unknown Evidence

```text
Real customer conversion
Incremental conversion lift
Incremental contribution
Customer Net Economic Value
Next-dollar economics
```

No real pilot evidence currently exists.

## Do Not Create False Precision

Avoid turning weak qualitative evidence into an arbitrary numeric confidence score such as:

```text
Evidence Confidence = 73%
```

unless the probability model behind that number is defensible.

Prefer explicit evidence states and documented gaps.

## Unknown Is Not Conditional

These are different:

```text
Conditional
=
we know the claim depends on a stated condition

Unknown
=
we lack evidence needed to assess the claim
```

Do not convert Unknown into a favorable conditional conclusion.

## Evidence Confidence Does Not Change the Value Number

Do not mechanically multiply:

```text
$100 value
×
60% confidence
=
$60 confidence-adjusted value
```

unless the percentage is a defensible probability of the economic state being modeled.

Confidence is primarily a decision-quality signal, not automatically a mathematical discount factor.

## Decision Relevance

Evidence requirements should increase with the consequence of the decision.

```text
Explore
→ assumptions may be acceptable

Pilot
→ technical + preliminary business evidence

Scale
→ stronger causal, operational, and economic evidence
```

The purpose of evidence confidence is not to demand perfect certainty.

It is to make clear what level of belief the current decision is relying on.

## Key Takeaways

- Economic attractiveness and evidence confidence are different questions.
- Confidence belongs to claims, not just to the workload.
- Technical evidence can be strong while business-value evidence is weak.
- Modeled evidence should remain visibly modeled.
- Unknown evidence should remain Unknown.
- Avoid arbitrary universal confidence scores.
- Stronger investment decisions should require stronger supporting evidence.
- Evidence confidence should inform the decision, not silently rewrite the economics.

## Next Step

Create an Evidence Confidence Record that summarizes the evidence supporting the workload's major technical, business, economic, and incremental claims without collapsing them into a universal score.