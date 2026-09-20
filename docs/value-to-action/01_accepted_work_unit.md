# Accepted Work Unit — v1

## Decision Question
What must be true before one AI interaction counts as useful, accepted work?

## Definition
One AI-addressable customer inquiry that receives a response satisfying the required application behavior and mandatory product guardrails.

## Acceptance Contract
An interaction is accepted only when it:

- handles the requested task correctly,
- remains grounded in supported menu information,
- respects explicit user constraints,
- abstains when evidence is insufficient,
- avoids unsupported facts,
- stays within Contoso Coffee scope.

## Current Evidence
The regression suite already tests:

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

## Current Gap
The current economics pipeline uses the behavior-rubric pass rate as `success_rate`.

That is not yet a formal Accepted Work metric because mandatory guardrails are evaluated separately.

## Key Distinction

```text
Attempted Interaction
        ↓
Technically Completed Response
        ↓
Accepted Work Unit
```

## Key Takeaway

This captures the most important lesson without adding unnecessary theory:

> **A model response is not automatically a successful business outcome.**

And it creates a clean progression from the current code:

```text
current:
cost / behavior success

next:
cost / accepted work

later:
full system cost / accepted work
```

## Next Step

Measure Accepted Work explicitly at the interaction level rather than approximating it from aggregate evaluator pass rates.