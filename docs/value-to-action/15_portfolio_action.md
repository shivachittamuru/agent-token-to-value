# Portfolio Action — v1

## Decision Question

Given the Workload Assessment and Decision Gates, what action should be taken now, why, what resources should be committed, and what evidence should trigger reassessment?

## Core Rule

The portfolio action should address the workload's primary decision deficit.

```text
Evidence Deficit
        → PROVE

Execution Deficit
        → OPTIMIZE

Structural Deficit
        → RESTRUCTURE

Attractive Incremental Economics
+
Required Gates Satisfied
        → SCALE
```

Other actions may be appropriate when continued operation is justified without expansion, when no near-term work is justified, or when the workload no longer has a continuing rationale.

## Canonical Actions

### SCALE

Commit additional resources to increase the workload's reach, capacity, or scope.

Appropriate when:

- the proposed increment is explicit,
- incremental value is established,
- incremental customer cost is sufficiently complete,
- Incremental Net Economic Value supports the investment,
- required evidence and resilience are sufficient,
- mandatory controls are satisfied.

Strong historical or modeled economics alone do not justify SCALE.

### SUSTAIN

Continue the current workload without a material expansion or restructuring.

Appropriate when:

- current operation has a continuing rationale,
- existing performance is acceptable,
- no material additional investment is currently justified,
- no urgent evidence, execution, or structural deficit requires intervention.

SUSTAIN is not the same as SCALE.

### OPTIMIZE

Invest specifically in improving execution efficiency, quality, reliability, cost, or operating performance.

Appropriate when:

- the workload's value case is sufficiently established,
- execution performance is the primary constraint,
- improving execution could materially improve economic performance.

Examples:

- excessive retries,
- high cost per Accepted Work,
- poor latency affecting business outcomes,
- excessive human intervention,
- avoidable tool/model consumption.

Do not choose OPTIMIZE merely because technical improvements are possible.

### PROVE

Invest in evidence needed to resolve a decision-critical uncertainty.

Appropriate when:

- the opportunity is plausible enough to justify further investigation,
- a material decision depends on evidence that is currently missing,
- a bounded experiment or pilot can reduce that uncertainty.

Examples:

- establish real eligible demand,
- observe downstream business outcomes,
- measure treatment/control conversion,
- establish incremental value,
- complete customer-cost evidence.

PROVE should have a specific evidence objective.

It is not permission for indefinite experimentation.

### RESTRUCTURE

Change the workload's operating, commercial, ownership, funding, control, or architectural structure.

Appropriate when the primary issue is not simply evidence or execution.

Examples:

- commercial model does not align with value/cost behavior,
- ownership is unclear,
- funding model is inappropriate,
- mandatory control architecture requires redesign,
- dependency or operating structure has materially changed.

RESTRUCTURE changes the system around the workload.

### PAUSE

Stop additional near-term investment while preserving the option to revisit the workload.

Appropriate when:

- there is no justified next unit of work,
- an external dependency or prerequisite must resolve first,
- evidence collection cannot currently change the decision,
- a mandatory blocker prevents responsible progress.

PAUSE should include a reassessment trigger.

It is not the same as RETIRE.

### RETIRE

End continuing investment or operation when there is no sufficient economic, strategic, mandatory, or dependency rationale for continuation.

RETIRE should be based on explicit reasoning rather than lack of attention or temporary uncertainty.

## Action Selection Principle

Do not select an action simply because it is eligible.

Ask:

> What is the primary reason the workload cannot move to the next justified economic state?

Then choose the action that addresses that constraint.

```text
Eligibility
      ↓
Primary Decision Deficit
      ↓
Portfolio Action
```

## Current Contoso Decision

### Decision Context

Determine what portfolio action is justified by the current evidence.

### What Is Established

- technical behavior is established in regression,
- Accepted Work is measurable,
- model inference cost is measured,
- modeled scenario economics appear attractive,
- modeled scenario sensitivity remains favorable under tested parameter stresses.

### What Is Missing

- real eligible-demand baseline,
- observed downstream business outcomes,
- treatment/control conversion,
- incremental business value,
- Total Relevant Customer Cost,
- next-dollar economics,
- realistic-volume capacity behavior.

### Primary Decision Deficit

The dominant constraint is:

```text
EVIDENCE DEFICIT
```

The main uncertainty is not whether the agent can technically answer the regression workload.

The uncertainty is whether deploying the workload produces incremental customer economic value.

### Selected Action

```text
PROVE
```

The workload has enough technical and modeled economic promise to justify collecting stronger business evidence, but not enough evidence to justify SCALE.

## PROVE Objective

Run a bounded real-world pilot designed to test:

```text
Real Eligible Demand
        ↓
Treatment / Control Assignment
        ↓
Business Outcome
        ↓
Incremental Conversion
        ↓
Incremental Contribution
        ↓
Total Relevant Customer Cost
        ↓
Incremental / Customer Economics
```

The pilot should reduce the uncertainties most likely to change the investment decision.

## Required Evidence

Prioritize:

1. actual AI-eligible unanswered demand,
2. treatment and control conversion,
3. observed order value and contribution economics,
4. Total Relevant Customer Cost,
5. human/recovery intervention,
6. realistic-volume capacity behavior.

## Resource Commitment

The appropriate resource commitment is not broad production scale.

It is a bounded evidence-producing investment:

```text
pilot instrumentation
+
treatment/control mechanism
+
business outcome linkage
+
cost attribution
+
defined evaluation period
```

A specific budget or staffing commitment should be supplied by the decision owner rather than fabricated by the framework.

## Decision Owner

The portfolio action requires an accountable decision owner.

If no owner has been assigned:

```text
decision_owner = Unknown
```

Do not fabricate ownership.

## Reassessment Trigger

Reassess the workload when the pilot has produced enough evidence to evaluate:

- incremental conversion,
- incremental contribution,
- Total Relevant Customer Cost,
- Incremental Net Economic Value,
- material control or operational issues.

The reassessment trigger should be evidence-based rather than an arbitrary calendar date when possible.

## What Could Change the Action

### PROVE → SCALE

Possible only if stronger evidence establishes attractive incremental economics and required gates are satisfied.

### PROVE → OPTIMIZE

If the pilot shows business value but execution inefficiency materially constrains that value.

### PROVE → RESTRUCTURE

If the primary constraint proves to be commercial, operating, ownership, funding, or control structure.

### PROVE → SUSTAIN

If current operation is justified but additional investment is not.

### PROVE → PAUSE

If the evidence cannot presently be obtained or an external blocker makes further work unjustified.

### PROVE → RETIRE

If stronger evidence removes the economic rationale and no strategic, mandatory, or dependency rationale supports continuation.

## Action Record

A Portfolio Action Record should preserve:

```text
workload_id
decision_id
decision_context

selected_action
primary_decision_deficit
action_rationale

required_work
required_evidence
resource_request

decision_owner
decision_date

reassessment_trigger
conditions_that_change_action
```

The action should remain traceable to the Decision Gate Record and Workload Assessment that supported it.

## No Permanent Decision

Portfolio actions are current decisions based on current evidence.

```text
Evidence changes
        ↓
Economics change
        ↓
Gate readiness changes
        ↓
Action may change
```

The framework should therefore treat every action as reassessable.

## Key Takeaways

- Eligibility and action selection are different steps.
- Select the action that addresses the primary decision deficit.
- PROVE addresses an evidence deficit.
- OPTIMIZE addresses an execution deficit.
- RESTRUCTURE addresses a structural deficit.
- SCALE requires justified incremental investment economics and satisfied gates.
- PAUSE preserves optionality when no justified near-term work exists.
- RETIRE requires a reason to stop, not merely missing evidence.
- Every action should specify what work happens next and what evidence triggers reassessment.

## Next Step

Create a Portfolio Action Record that selects the currently justified action, defines the work it authorizes, and records the evidence-based reassessment trigger.