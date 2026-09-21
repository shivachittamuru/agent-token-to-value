# Decision Gates — v1

## Decision Question

What conditions must be evaluated before a workload can legitimately move toward a portfolio action such as Scale, Sustain, Optimize, Prove, Restructure, Pause, or Retire?

## Core Rule

Decision gates are not a scoring system.

```text
Strong Dimension
        +
Failed Critical Gate
        ≠
Automatic Approval
```

A decision-critical requirement should remain visible rather than being averaged away by stronger dimensions.

## Assessment vs Decision

The Workload Assessment answers:

```text
What is established?
What is modeled?
What is Unknown?
What could change the decision?
```

Decision Gates ask:

```text
Given that evidence,
which actions are currently supportable?
```

The gates constrain the action space.

They do not automatically choose the final action.

## Gate Structure

Evaluate the workload across independent gates.

```text
Strategic / Mandatory
        ↓
Value
        ↓
Evidence
        ↓
Value Resilience
        ↓
Incremental Economics
        ↓
Commercial Fit
        ↓
Responsible AI / Risk / Control
        ↓
Eligible Action Set
```

A gate may be:

```text
PASS
CONDITIONAL
FAIL
UNKNOWN
NOT_APPLICABLE
```

These states must remain distinct.

## 1. Strategic / Mandatory Gate

Ask:

> Is this workload required or strategically necessary independent of near-term economics?

Examples may include:

- regulatory obligation,
- contractual requirement,
- security requirement,
- critical platform capability,
- strategic experimentation.

Possible states:

```text
PASS
CONDITIONAL
FAIL
UNKNOWN
NOT_APPLICABLE
```

A mandatory workload may justify continued investment even when direct economics are weak.

That does not make weak economics strong.

It means the decision rationale is different.

## 2. Value Gate

Ask:

> Is economically meaningful value established at the evidence level required for the proposed action?

Possible evidence states include:

```text
modeled_only
observed_not_incremental
incremental_value_established
unknown
```

The gate requirement depends on the decision.

For example:

```text
Explore / Prove
→ modeled value may be sufficient

Scale
→ generally requires stronger incremental evidence
```

Do not treat a large modeled value estimate as equivalent to proven incremental value.

## 3. Evidence Gate

Ask:

> Is the evidence strong enough for the consequence of the proposed decision?

Relevant evidence may include:

- technical performance,
- business outcomes,
- counterfactual evidence,
- economic inputs,
- cost completeness,
- production representativeness.

The required evidence should increase with the consequence of the action.

```text
Explore
<
Pilot
<
Scale
```

Unknown is not the same as Conditional.

```text
UNKNOWN
=
we do not yet know

CONDITIONAL
=
the requirement is satisfied only under an explicit known condition
```

## 4. Value Resilience Gate

Ask:

> Does the economic conclusion survive plausible adverse conditions?

Consider:

- break-even boundaries,
- sensitive drivers,
- combined stress,
- structural risks,
- capacity thresholds,
- persistence over time.

Modeled scenario resilience may support exploration.

It should not be silently promoted into evidence-backed production resilience.

## 5. Incremental Economics Gate

Ask:

> Does the proposed next increment create more economic value than additional customer cost?

The relevant equation is:

```text
ΔNEV
=
Incremental Value
-
Incremental Customer Cost
```

For expansion decisions, this gate should consider:

- explicit proposed increment,
- matching economic basis,
- established incremental value,
- complete incremental customer cost.

Historical workload economics do not automatically satisfy this gate.

## 6. Commercial Fit Gate

Ask:

> Does the commercial model align customer payment with the value and cost behavior of the workload?

Consider:

- subscription,
- consumption,
- hybrid,
- outcome-linked models,
- committed capacity,
- cost variability,
- who bears scale risk.

A workload may create technical value but have poor commercial fit.

Commercial fit should remain separate from technical performance.

## 7. Responsible AI / Risk / Control Gate

Ask:

> Are mandatory risk, safety, compliance, security, and control requirements satisfied?

Some requirements are non-compensable.

```text
Very high economic value
+
failed mandatory safety/control requirement
≠
approval
```

Examples may include:

- security controls,
- privacy obligations,
- regulatory requirements,
- responsible AI requirements,
- mandatory human approval,
- auditability,
- operational safeguards.

These requirements should be represented explicitly rather than converted into economic penalties unless that is genuinely appropriate.

## Non-Compensable Gates

Some gates must not be overridden by strong economics.

Examples include:

```text
mandatory safety requirement
security requirement
regulatory requirement
explicit governance control
```

A composite score must never allow:

```text
excellent economics
```

to numerically cancel:

```text
failed mandatory control
```

## Current Contoso Gate Readiness

The current evidence suggests:

### Strategic / Mandatory

```text
UNKNOWN / NOT YET ASSESSED
```

No explicit strategic or mandatory requirement has been recorded.

### Value

```text
MODELED ONLY
```

Attractive scenario economics exist.

Incremental economic value is not established.

### Evidence

```text
INCOMPLETE
```

Technical regression evidence is strong.

Real business outcomes and causal evidence remain Unknown.

### Value Resilience

```text
MODELED SCENARIO
```

Scenario stress analysis exists.

Evidence-backed production resilience is not established.

### Incremental Economics

```text
NOT ESTABLISHED
```

No explicit next-dollar increment has been defined and evidenced.

### Commercial Fit

```text
UNKNOWN
```

No commercial-meter assessment has yet been performed.

### Responsible AI / Risk / Control

```text
NOT YET ASSESSED
```

No decision-gate record has yet established whether mandatory requirements apply or are satisfied.

## Why UNKNOWN Must Remain Distinct

Consider:

```text
Commercial Fit = UNKNOWN
```

This does not mean:

```text
Commercial Fit = FAIL
```

It means the decision requires either:

- more evidence,
- an explicit assessment,
- or a determination that the gate is not applicable.

Similarly:

```text
Responsible AI Gate = UNKNOWN
```

must not silently become PASS.

## Gate Applicability

Not every gate has equal relevance to every decision.

For example:

```text
early exploration
```

may not require complete incremental economics.

But:

```text
large-scale expansion
```

may require:

- stronger evidence,
- stronger value resilience,
- complete incremental economics,
- satisfied mandatory controls.

Gate requirements should therefore be interpreted relative to the proposed action.

## Decision Gate Record

A gate record should preserve:

```text
workload_id
decision_id
decision_context

strategic_mandatory_gate
value_gate
evidence_gate
resilience_gate
incremental_economics_gate
commercial_fit_gate
rai_risk_control_gate

blocking_gates
conditional_gates
unknown_gates

eligible_actions
ineligible_actions
```

The gate record should explain why a state was assigned.

## Gate Outcomes Do Not Yet Select the Action

Decision Gates determine what actions are supportable.

For example:

```text
Scale
```

may be ineligible because incremental evidence is missing.

That does not automatically mean:

```text
Prove
```

must be selected.

The final portfolio action should consider:

- what problem actually remains,
- what work would change the decision,
- resource competition,
- ownership,
- reassessment timing.

That belongs to the Portfolio Action Record.

## Key Takeaways

- Decision gates constrain actions; they do not create a score.
- Critical failed gates cannot be averaged away.
- Unknown, Conditional, Fail, and Not Applicable are different states.
- Strong modeled economics do not automatically satisfy the Value or Evidence gates for scaling.
- Incremental economics matter most when evaluating additional investment.
- Commercial fit is separate from technical value.
- Mandatory Responsible AI, security, regulatory, and governance controls may be non-compensable.
- Gate requirements should reflect the consequence of the proposed action.
- The gate model prepares the action decision without silently making it.

## Next Step

Create a Decision Gate Record that evaluates each gate independently and determines which portfolio actions are currently eligible without yet selecting the final action.