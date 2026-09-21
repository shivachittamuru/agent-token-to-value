# Pilot Evidence Plan — v1

## Decision Question

What bounded real-world pilot would produce enough evidence to test whether the Contoso AI workload creates incremental business value?

## Business Hypothesis

During periods when staff cannot respond, an AI-assisted interaction may preserve customer intent and recover orders that would otherwise have been lost.

The pilot must test the links:

```text
Eligible Inquiry
      ↓
AI Treatment
      ↓
Accepted Work
      ↓
Customer Continues
      ↓
Order Completed
      ↓
Incremental Conversion Lift
      ↓
Incremental Contribution
```

## Primary Counterfactual

The key question is:

> What would have happened to the same type of eligible inquiry without AI assistance?

The preferred design is a bounded treatment/control comparison among otherwise similar eligible inquiries.

```text
Eligible, staff-unavailable inquiry
              ↓
         Assignment
          /       \
      AI Treatment   Control
          ↓             ↓
    customer outcome  customer outcome
          \             /
             Compare
```

## Unit of Analysis

The primary unit is:

**one AI-eligible customer inquiry occurring during a defined staff-unavailable condition.**

Assignment must occur before observing whether the AI response becomes Accepted Work.

## Treatment and Control

### Treatment

Eligible inquiry receives the AI-assisted response.

### Control

Eligible inquiry follows the normal no-AI baseline process for the pilot design.

The control must represent a credible version of what would happen without the AI capability.

## Primary Outcome

The primary business outcome should be:

```text
Order Conversion Rate
=
Completed Orders
────────────────────
Eligible Inquiries
```

Compare:

```text
Treatment Conversion Rate
-
Control Conversion Rate
=
Incremental Conversion Lift
```

This is more defensible than assuming that every order following an AI interaction was recovered by AI.

## Economic Translation

If the pilot establishes an incremental conversion lift:

```text
Incremental Conversion Lift
        ×
Eligible Inquiry Volume
        ↓
Incremental Orders

Incremental Orders
        ×
Observed Average Order Value
        ×
Contribution Margin
        ↓
Incremental Contribution
```

Economic value should be based on the incremental difference between treatment and counterfactual, not total treatment-arm orders.

## Accepted Work Role

Accepted Work remains an important technical signal, but it is not the treatment definition.

```text
Treatment Assignment
        ↓
AI Executes
        ↓
Accepted / Rejected Work
        ↓
Business Outcome
```

Use Accepted Work to understand why treatment succeeds or fails.

Do not estimate causal value by comparing only Accepted Work interactions against control.

That would condition the analysis on a post-treatment result.

## Minimum Pilot Evidence

Each eligible interaction should capture:

### Assignment

- interaction ID,
- eligibility status,
- treatment/control assignment,
- staff-availability condition,
- assignment timestamp.

### AI Evidence

For treatment interactions:

- Execution Record,
- Accepted Work status,
- model/tool consumption,
- execution cost evidence.

### Business Outcome

- customer engagement after the interaction,
- completed order status,
- opaque order ID,
- observed order value,
- outcome timestamp,
- evidence source.

### Experiment Evidence

- counterfactual method,
- experiment/pilot ID,
- treatment/control assignment,
- attribution window,
- exclusions or protocol deviations.

## Attribution Window

The pilot must define how long after the inquiry an order may reasonably be linked to that interaction.

For example:

```text
Inquiry
   ↓
Defined Attribution Window
   ↓
Qualifying Order Event
```

The window should be chosen before analyzing results rather than adjusted afterward to improve the outcome.

## Primary Analysis

The primary analysis should use all eligible assigned interactions.

```text
Treatment:
orders / eligible assigned inquiries

Control:
orders / eligible assigned inquiries
```

This preserves the original assignment and avoids selecting only technically successful treatment cases.

## Diagnostic Analysis

Within the treatment group, also examine:

- Accepted Work rate,
- conversion after Accepted Work,
- conversion after rejected work,
- tool/retry patterns,
- latency,
- execution cost.

These help explain performance but should not replace the primary treatment/control comparison.

## Evidence States

The pilot should preserve the distinction between:

```text
Observed
Assumed
Unknown
```

Do not use the existing scenario assumptions to fill missing pilot observations.

Examples:

- observed order value should replace assumed AOV when available,
- measured treatment/control conversion should replace assumed conversion when sufficiently credible,
- unresolved full execution costs should remain incomplete.

## Pilot Guardrails

- Define eligibility before assignment.
- Assign treatment before observing AI quality.
- Do not remove failed AI interactions from the treatment denominator.
- Do not treat Accepted Work as proof of business value.
- Do not treat observed treatment orders as incremental without comparison.
- Preserve control-group integrity and avoid contamination where practical.
- Define the attribution window before analysis.
- Record exclusions and missing evidence explicitly.
- Keep technical, business, and causal evidence linked by stable identity.

## Pilot Success Is Not a Single Threshold

The pilot should reduce uncertainty across several questions:

```text
Does AI produce Accepted Work reliably?
        ↓
Does treatment improve the customer journey?
        ↓
Does conversion improve relative to control?
        ↓
Is the lift economically meaningful?
        ↓
Does value persist after execution and operating cost?
```

A technically successful pilot may still fail to establish incremental business value.

A promising business signal may still require more evidence before broader scaling.

## Evidence Needed Before Broader Investment

The pilot should ideally provide evidence for:

- real eligible inquiry volume,
- actual unanswered-demand baseline,
- Accepted Work rate under real traffic,
- treatment and control conversion rates,
- incremental conversion lift,
- observed order value,
- contribution margin,
- execution and recovery costs,
- operational intervention rate,
- persistence across representative periods.

## Current Status

Today:

```text
Technical execution evidence
        =
Measured

Accepted Work
        =
Measured

Business outcomes
        =
Unknown

Incrementality
        =
Unknown
```

The pilot is the mechanism for converting those business-value Unknowns into observed evidence.

## Key Takeaways

- A pilot should test the causal chain, not merely demonstrate that the AI works.
- Treatment assignment must be defined before observing AI success.
- Accepted Work is diagnostic evidence, not the counterfactual.
- Incremental value comes from treatment-versus-counterfactual difference.
- Failed treatment interactions remain part of the causal denominator.
- Real pilot observations should progressively replace scenario assumptions.
- The purpose of the pilot is to reduce uncertainty enough to support a better investment decision.

## Next Step

Define the minimum experiment metadata and pilot outcome schema required to populate the Business Outcome Evidence Record when real-world pilot data becomes available.