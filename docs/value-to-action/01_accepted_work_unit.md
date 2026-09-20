# Accepted Work Unit — v1

## Decision Question

What must be true before one AI interaction counts as useful, accepted work?

## Definition

One AI-addressable customer inquiry that receives a response satisfying the required application behavior and all mandatory product guardrails.

## Acceptance Contract

An interaction counts as Accepted Work only when it:

- handles the requested task correctly,
- remains grounded in supported menu information,
- respects explicit user constraints,
- abstains when evidence is insufficient,
- avoids unsupported facts,
- stays within Contoso Coffee scope.

The contract can evolve as additional mandatory controls are introduced, such as safety, privacy, policy, business rules, or required human approval.

## Current Evaluator Coverage

The regression suite tests:

- exact retrieval,
- filtering,
- arithmetic,
- semantic recommendation,
- abstention,
- hallucination resistance,
- ambiguity,
- scope adherence,
- exhaustive retrieval,
- range filtering.

The current evaluator design separates:

- `contoso_behavior_rubric` — did the agent do the job correctly?
- `contoso_scope_adherence` — did the agent stay within its job?

## Acceptance Rule

Accepted Work is determined per interaction.

```text
Behavior passes
        +
All mandatory guardrails pass
        ↓
Accepted Work
```

For the current implementation:

```text
Accepted
=
behavior pass
AND
scope pass
```

This is an implementation of the broader principle:

> Accepted Work = quality-qualified output satisfying all mandatory control floors.

## Row-Level Measurement

Acceptance must be calculated from the evaluator results for the same interaction.

Do not estimate Accepted Work by multiplying aggregate pass rates.

For example:

```text
behavior pass rate = 90%
scope pass rate = 90%

90% × 90% ≠ valid Accepted Work rate
```

The same interactions may fail both criteria, or different interactions may fail each criterion.

Acceptance must therefore be evaluated row by row.

## Missing Evidence

An attempted interaction with no row-level acceptance evidence does not count as Accepted Work.

```text
Attempted interaction
        +
No acceptance evidence
        ↓
Not accepted
```

Missing evidence is surfaced explicitly rather than silently shrinking the denominator.

## Key Distinction

```text
Attempted Interaction
        ↓
Technically Completed Response
        ↓
Quality + Guardrail Verification
        ↓
Accepted Work Unit
```

A technically completed response is not automatically useful work.

## Economic Role

Accepted Work becomes the denominator for economic efficiency.

```text
Model Cost
──────────────
Accepted Work

later:

Full Execution Cost
───────────────────
Accepted Work
```

Resources consumed by rejected interactions remain in the numerator because that consumption still occurred.

## Current Evidence

The implementation now records:

- attempted interactions,
- evaluated interactions,
- accepted interactions,
- rejected interactions,
- missing evaluation evidence,
- Accepted Work rate,
- tokens per Accepted Work,
- model cost per Accepted Work.

Acceptance is joined back to execution evidence by stable interaction identity.

## Key Takeaways

- A model response is not automatically useful work.
- Accepted Work requires both task success and mandatory control compliance.
- Acceptance should be evaluated per interaction, not inferred from aggregate pass rates.
- Missing acceptance evidence should not be treated as success.
- Failed interactions still consume resources and therefore affect the economics of Accepted Work.
- The Accepted Work definition should remain stable even if the evaluator implementation changes.

## Next Step

Define the complete system boundary required to produce Accepted Work so execution economics can extend beyond model inference alone.