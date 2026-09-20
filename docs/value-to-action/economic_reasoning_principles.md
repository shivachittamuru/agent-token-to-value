# Economic Reasoning Principles

These principles generalize beyond the Contoso Coffee example.

## 1. The model is not the system
Model inference is only one component of the system required to produce useful work.

Always distinguish:

Model Cost
→ Full Execution Cost
→ Total Customer Cost

## 2. Technical boundary ≠ economic boundary
Something can participate in the solution without being a per-interaction production cost.

Example:
Regression evaluators and judge-model calls are economically real, but they are usually lifecycle/governance costs rather than costs incurred for every customer interaction.

## 3. Classify costs before adding them
Useful categories include:

- Direct execution
- Allocated operating
- Human / recovery
- Lifecycle / evidence
- Implementation

Do not combine them blindly into one denominator.

## 4. Cost behavior matters
A cost can be:

- variable,
- fixed / committed,
- allocated shared,
- unknown.

Average cost and marginal cost answer different questions.

Average cost asks:
"What does the workload cost on average?"

Marginal cost asks:
"What additional cost is caused by serving more work?"

Scaling decisions depend heavily on the second question.

## 5. Failure has multiple economic effects
Failure can create:

- wasted execution,
- retry/recovery cost,
- human rework,
- downstream business consequence.

Keep these distinct so the same loss is not double-counted.

## 6. Required human control is not automatically waste
If review or approval is intentionally required for safety, quality, or policy, it is part of the operating design.

It should be costed, but not mislabeled as inefficiency.

## 7. Unknown does not mean zero
If a relevant cost cannot yet be measured, record it as Unknown.

Do not silently exclude it and present an incomplete denominator as total cost.

## 8. Match the denominator to the decision
Different decisions require different economics.

Model optimization:
Model Cost / Accepted Work

Architecture efficiency:
Full Execution Cost / Accepted Work

Business viability:
Total Customer Cost versus Economic Value

Expansion decision:
Incremental Value versus Incremental Cost

## 9. Telemetry is not economics
Observing a resource does not automatically tell us its cost. For example, a tool-call count is evidence of activity, not necessarily a per-call dollar cost.

```text
Telemetry
+
Pricing / Allocation Rule
+
Decision Context
=
Economic Attribution
```

## 10. Average economics and incremental economics answer different decisions

Average cost helps assess whether a workload is economically healthy.

Incremental cost helps assess whether additional scale is attractive.

A workload can have high average cost but low marginal cost, or the reverse.

## 11. Some AI infrastructure costs are step-functions

Infrastructure cost may stay flat across a range of usage and then jump when capacity must increase.

Treating all infrastructure as smoothly variable can distort scaling decisions.

## 12. Do not monetize a metric without a causal bridge

Latency, retries, tool calls, and human touches may matter economically, but they should not be assigned a dollar value unless the relationship is defensible.

Example:

```text
Latency
≠
Economic loss

Latency
→ lower conversion / SLA penalty / labor delay
→ evidenced economic effect
```

## 13. Cost allocation is a decision model, not a physical truth

Shared costs can often be allocated in several defensible ways.

The allocation rule should match the decision being made and remain visible rather than being hidden inside a final number.

## 14. Architecture determines the correct cost model
The same functional capability may have very different economics depending on how it is provisioned.

A dedicated service may behave like fixed or step-function capacity.
A serverless service may behave like usage-based consumption.

Do not apply one pricing model to both.

## 15. Known zero and Unknown are different
A component can legitimately have no additional charge under a given architecture.

That is different from lacking evidence.

```text
Known zero
≠
Unknown
```

## 16. A partial cost model should identify itself as partial

If economically relevant components remain Unknown or unallocated, do not label the measured subset as total or full cost.

Precision in naming is part of economic rigor.

## 17. Cost completeness is itself evidence

A workload can have an accurate measured model cost while still having incomplete execution economics.

Decision confidence should depend not only on the number, but also on how complete the denominator is.

## 18. Zero, Unknown, and Not Applicable are different economic states

Do not collapse them.

- **Zero** — evidence supports that no additional cost is attributed.
- **Unknown** — the component matters, but cost evidence is incomplete.
- **Not applicable** — the component is outside the workload/system design.

These states imply different decisions.

## 19. Cost completeness should travel with the number

A cost number without its completeness state can be misleading.

For example:

```text
Known direct execution cost = $0.007
Cost completeness = partial
```

## 20. Failed work still belongs in the numerator

Resources consumed by rejected work do not disappear from the economics.

```text
Total Execution Consumption
───────────────────────────
Accepted Work Units
```

naturally makes failures increase the cost of useful production.

Do not remove failed executions from the numerator merely because they produced no Accepted Work.

## 21. Acceptance rate has an economic penalty

When attempts have similar cost:

```text
Cost per Accepted Work
≈
Cost per Attempt
───────────────
Acceptance Rate
```

For example, a 90% acceptance rate makes the unit cost of useful work roughly 11.1% higher than the average cost of an attempt.

Quality therefore affects economics even when the underlying model price does not change.

## 22. Partial economics can still be decision-useful

An incomplete cost model is not automatically useless.

A precisely labelled metric such as:

```text
Known Direct Cost / Accepted Work
Cost Completeness: Partial
```

can support optimization and comparison while additional cost evidence is being established.

The problem is not incompleteness itself.

The problem is presenting partial economics as complete economics.

## 23. Cost completeness is separate from cost precision

A measured number can be highly precise while still representing only part of the economic system.

For example:

```text
Known direct execution cost = $0.075589
```

may be precisely measured while Search, observability, and human recovery remain unallocated.

More decimal places do not make an incomplete denominator complete.

## 24. Accepted Work is not Business Value

Accepted Work proves that the AI system produced a qualifying output.

It does not prove that the workflow advanced, a business outcome occurred, or economic value was created.

```text
Accepted Work
→ Workflow Outcome
→ Business Outcome
→ Economic Value
```

Each transition requires its own evidence.

## 25. Correlation is not incrementality

A business event occurring after an AI interaction does not prove that the AI caused it.

```text
Order after AI
≠
Order caused by AI
```

Economic value should be based on outcomes that are incremental relative to a defensible counterfactual.

## 26. Stronger value claims require stronger counterfactual evidence

The more consequential the investment decision, the stronger the evidence needed to establish what would have happened without the AI capability.

A modeled assumption may be sufficient for exploration.

A scaling decision may require a pilot, control group, phased rollout, or another defensible comparison.

## 27. Every arrow in the value chain is an evidence claim

A value chain such as:

```text
AI Work
→ Accepted Work
→ Customer Action
→ Business Outcome
→ Economic Value
```

should not be treated as one assumption.

Each arrow represents a separate claim that can have different evidence quality.

## 28. A pilot should reduce decision uncertainty, not merely prove technical feasibility

A technically successful pilot is insufficient if the important business-value assumptions remain unchanged.

The pilot should be designed to collect evidence on the links most likely to change the investment decision.

## 29. Unknown outcome and negative outcome are different states

Missing downstream evidence does not mean the business outcome failed.

```text
order_completed = False
```

means evidence shows no order occurred.

```text
order_completed = Unknown
```

means the outcome was not observed.

Conflating the two can materially distort business-value estimates.

## 30. Technical evidence and business evidence have different clocks

Execution telemetry is often available immediately.

Business outcomes may occur seconds, hours, days, or weeks later and may live in another system.

The evidence model must therefore support delayed joining by stable identity rather than assuming all evidence exists at execution time.

## 31. Observed outcome and attributable outcome are separate claims

An observed business event can be real while its incrementality remains unknown.

```text
Observed Order = True
Incremental Order = Unknown
```

is a valid and often necessary evidence state.

Do not force causal certainty merely because the downstream event is measurable.

## 32. Do not use assumptions to fill missing observations

A modeled conversion rate can support scenario analysis.

It must not be used to fabricate observed customer outcomes.

```text
Assumption
≠
Observation
```

Keep scenario models and evidence records separate.