# Pilot Evidence Schema — v1

## Decision Question

What experiment metadata must be captured so downstream business outcomes can be interpreted as credible pilot evidence?

## Core Rule

Business outcome evidence is not enough by itself.

It must be interpreted in the context of:

```text
Eligibility
    +
Assignment
    +
Exposure
    +
Outcome Window
    ↓
Pilot Evidence
```

## Minimum Pilot Record

Each eligible interaction should be capable of carrying:

| Field | Meaning |
|---|---|
| `pilot_id` | Stable identifier for the pilot or experiment |
| `interaction_id` | Stable interaction identity |
| `eligible` | Whether the interaction met the predefined pilot eligibility rules |
| `assignment` | `treatment` or `control` |
| `assigned_at_utc` | Time assignment occurred |
| `staff_unavailable` | Whether the qualifying staff-unavailable condition was present |
| `attribution_window_minutes` | Predefined period in which downstream outcomes may be linked |
| `protocol_deviation` | Whether the interaction deviated from the intended experiment protocol |
| `protocol_deviation_reason` | Explanation when a deviation occurred |

## Why Assignment Must Be Explicit

The treatment population is defined by assignment, not by later AI success.

```text
Eligible Inquiry
      ↓
Assignment
   /      \
Treatment  Control
```

Only after assignment can we observe:

```text
AI execution
Accepted Work
Customer behavior
Order outcome
```

This prevents Accepted Work from becoming a hidden selection criterion.

## Eligibility

Eligibility should be established before treatment assignment.

For Contoso, eligibility may require conditions such as:

```text
customer inquiry received
+
menu-related request
+
staff unavailable
+
appropriate for AI handling
```

The exact production criteria should be specified before the pilot begins.

## Assignment

`assignment` should represent the intended experimental treatment:

```text
treatment
=
AI capability offered

control
=
normal no-AI baseline process
```

Assignment should remain recorded even if treatment execution later fails.

A failed AI interaction remains part of the treatment population.

## Exposure vs Assignment

Assignment and actual exposure are different concepts.

For example:

```text
assignment = treatment
```

may be known even when:

```text
AI response fails to complete
```

Do not silently reclassify failed treatment interactions as control.

## Attribution Window

The pilot must define the time period in which a downstream event may reasonably be associated with the originating inquiry.

Example:

```text
Inquiry at 10:00
        ↓
30-minute attribution window
        ↓
Qualifying order before 10:30
```

The window should be predefined rather than selected after observing results.

## Protocol Deviations

Real pilots may not execute perfectly.

Examples include:

- treatment assigned but AI unavailable,
- control interaction receives unintended AI assistance,
- staff intervenes unexpectedly,
- duplicate interaction,
- missing downstream telemetry.

These should remain in the evidence record rather than being silently removed.

## Evidence Join

The intended evidence chain becomes:

```text
Pilot Assignment Record
        │
        │ interaction_id
        ▼
Execution Record
        │
        ▼
Accepted Work
        │
        ▼
Business Outcome Evidence
        │
        ▼
Treatment / Control Analysis
```

Stable identity allows technical, experimental, and business evidence to remain independently sourced but analytically connected.

## Current Regression Environment

The existing regression suite is not a real pilot.

Therefore:

```text
pilot_id = None
eligible = None
assignment = None
assigned_at_utc = None
staff_unavailable = None
attribution_window_minutes = None
protocol_deviation = None
protocol_deviation_reason = None
```

These values should remain Unknown rather than being fabricated from the synthetic evaluation dataset.

## Analysis Boundary

Only pilot data with credible experiment metadata should later support statements such as:

```text
Treatment conversion
Control conversion
Incremental conversion lift
```

Synthetic regression interactions may continue to support:

```text
technical quality
execution economics
Accepted Work
```

but not causal business claims.

## Key Takeaways

- Experimental context must travel with business outcome evidence.
- Eligibility must be defined before treatment assignment.
- Assignment must be preserved even when treatment execution fails.
- Treatment assignment and Accepted Work are different variables.
- Attribution windows should be predefined.
- Protocol deviations should be visible rather than silently excluded.
- Synthetic regression data should not be promoted into pilot evidence.

## Next Step

Implement the Pilot Evidence Record and preserve experiment metadata as Unknown in the current regression environment while allowing future real-world pilot events to populate it.