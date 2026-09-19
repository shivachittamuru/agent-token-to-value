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
The regression suite already evaluates:

- exact retrieval
- filtering
- arithmetic
- semantic recommendation
- abstention
- hallucination resistance
- ambiguity
- scope adherence
- exhaustive retrieval
- range filtering

## Current Gap
The code currently uses the behavior-rubric pass rate as `success_rate`.

That is not yet a formal Accepted Work metric because mandatory guardrails are evaluated separately.

## Key Takeaway
A completed model response is not automatically useful work.

Accepted Work is the smallest unit we are willing to count toward business value.

## Next Step
Represent Accepted Work explicitly in the evaluation/economics pipeline and calculate cost per accepted interaction.