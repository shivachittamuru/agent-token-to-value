# Workload Assessment — v1

## Decision Question

What does the available technical, business, economic, and resilience evidence currently justify us saying about this workload?

## Core Rule

Do not collapse different dimensions into a universal workload score.

Keep them visible:

```text
Value Performance
        +
Evidence Confidence
        +
Value Resilience
        +
Incremental Economics
        ↓
Workload Assessment
```

The assessment summarizes the evidence.

It does not yet choose the portfolio action.

## Assessment Dimensions

### 1. Technical Performance

Ask:

- Does the system reliably produce Accepted Work?
- What technical failures remain?
- What execution evidence is available?

### 2. Economic Value

Ask:

- Is value modeled, observed, or incremental?
- What economic numerator is justified?
- Is Customer Net Economic Value established?

### 3. Evidence Confidence

Ask:

- Which important claims are measured?
- Which are modeled?
- Which remain Unknown?
- Is a credible counterfactual available?

### 4. Value Resilience

Ask:

- How sensitive is the economic conclusion to important drivers?
- What break-even boundaries are known?
- Which structural risks remain unresolved?

### 5. Incremental Economics

Ask:

- Is a proposed investment increment defined?
- Is incremental value established?
- Is incremental customer cost established?
- Is Incremental Net Economic Value established?

These dimensions should remain independent.

## Current Contoso Assessment

### Technical Performance

```text
Status: ESTABLISHED IN REGRESSION
```

Evidence includes:

- per-interaction execution records,
- model/token consumption,
- tool activity,
- latency,
- Accepted Work evaluation,
- quality and scope guardrails.

This supports claims about technical behavior in the regression environment.

It does not establish production customer outcomes.

### Execution Economics

```text
Status: PARTIAL
```

Established:

- model inference cost,
- known direct execution cost,
- cost per attempt,
- cost per Accepted Work.

Not yet established:

- Azure AI Search economic attribution,
- observability allocation,
- human/recovery cost,
- Full Execution Cost.

### Business Outcome Evidence

```text
Status: UNKNOWN
```

Not yet observed:

- customer engagement after AI,
- completed orders attributable to the interaction,
- observed order value,
- realized contribution.

### Incrementality

```text
Status: UNKNOWN
```

There is currently:

- no real pilot assignment,
- no treatment/control evidence,
- no measured incremental conversion lift.

Therefore observed or modeled downstream outcomes cannot be called incremental value.

### Economic Value

```text
Status: MODELED ONLY
```

The current scenario model produces:

- modeled recovered contribution,
- modeled AI Value Multiple,
- break-even conversion analysis.

These remain scenario economics.

Customer Net Economic Value is not established.

### Incremental / Next-Dollar Economics

```text
Status: NOT ESTABLISHED
```

There is currently:

- no explicit proposed increment,
- no incremental value evidence,
- no incremental customer cost,
- no Incremental Net Economic Value.

Historical modeled economics therefore do not answer the next-dollar question.

### Value Resilience

```text
Scope: MODELED SCENARIO
Classification: NOT CLASSIFIED
```

Current scenario analysis can stress:

- conversion,
- average order value,
- contribution margin,
- inference-cost assumptions,
- combined adverse conditions.

The modeled economics remain well above the current model-cost break-even boundary across the tested scenarios.

However, structural Unknowns remain:

- real incremental conversion,
- real eligible-demand baseline,
- Total Relevant Customer Cost,
- human/recovery economics,
- capacity step-functions.

Therefore modeled resilience must not be interpreted as production economic resilience.

## Evidence Profile

The current workload can be summarized as:

| Claim | Evidence State |
|---|---|
| AI execution occurred | Measured |
| Token/model consumption | Measured |
| Accepted Work | Measured in regression |
| Tool activity | Measured |
| Known direct execution cost | Measured |
| Full Execution Cost | Partial / Unknown |
| Business outcome | Unknown |
| Customer conversion | Unknown |
| Incremental conversion | Unknown |
| Economic contribution | Modeled |
| Customer Net Economic Value | Unknown |
| Incremental Net Economic Value | Unknown |
| Modeled resilience | Available |
| Evidence-backed incremental resilience | Unknown |

## What the Current Evidence Supports

We can currently say:

> The Contoso workload has measurable technical execution, explicit Accepted Work evidence, and attractive modeled scenario economics relative to model inference cost.

We can also say:

> The modeled economics remain favorable under the currently tested parameter stresses.

We cannot yet say:

> The workload has demonstrated realized customer ROI.

We cannot yet say:

> The workload has demonstrated positive incremental business value.

We cannot yet say:

> Additional investment has positive incremental economics.

## Primary Decision Gaps

The highest-value evidence gaps are those that affect the transition from modeled opportunity to investment evidence.

### Business Demand

- actual unanswered-demand baseline,
- real AI-eligible volume.

### Business Outcome

- customer continuation,
- completed orders,
- observed order value.

### Causal Evidence

- treatment/control conversion,
- incremental conversion lift.

### Customer Economics

- Total Relevant Customer Cost,
- human/recovery economics,
- operational cost allocation.

### Scale Economics

- explicit proposed increment,
- incremental cost behavior,
- capacity step-functions.

## Evidence Priorities

Evidence collection should prioritize claims that are both:

```text
high uncertainty
+
high decision sensitivity
```

For Contoso, this suggests prioritizing:

1. real eligible-demand baseline,
2. treatment/control conversion evidence,
3. observed order economics,
4. Total Relevant Customer Cost,
5. operational and capacity behavior at realistic volume.

## Assessment Boundary

The Workload Assessment is not a portfolio decision.

It answers:

```text
What is established?
What is modeled?
What is Unknown?
What could change the decision?
```

The eventual action may be:

```text
Scale
Sustain
Optimize
Prove
Restructure
Pause
Retire
```

but that decision belongs to the next phase.

## No Universal Score

Do not calculate:

```text
Technical Score
+
Economic Score
+
Confidence Score
+
Resilience Score
=
Overall Workload Score
```

A composite score can hide important failed gates.

For example:

```text
very strong modeled economics
+
no causal business evidence
```

should not become a high-confidence investment recommendation merely because the average score is high.

## Key Takeaways

- Workload assessment is multi-dimensional.
- Strong technical evidence does not imply strong business-value evidence.
- Attractive modeled economics do not establish incremental value.
- Modeled resilience does not establish production resilience.
- Unknown is a meaningful assessment state.
- Decision-critical gaps should remain visible rather than being averaged away.
- The assessment prepares the decision; it does not make the decision.

## Next Step

Translate the Workload Assessment into an explicit portfolio decision using decision gates rather than a composite score.