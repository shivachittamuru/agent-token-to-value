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

## 33. Business evidence should carry provenance

A downstream value claim should identify where the supporting evidence came from.

```text
Outcome
+
Evidence Source
+
Observation Time
=
Traceable Business Evidence
```

An outcome field without provenance may be useful as raw data, but it should not silently become trusted evidence for an investment decision.

Stable identity tells us what the evidence belongs to.

Provenance tells us why we should believe it.

## 34. Define treatment before observing success

Causal analysis should compare groups based on assignment made before the outcome is known.

Do not define the AI treatment group as only the interactions that later became Accepted Work.

That selects on a post-treatment result and can overstate value.

## 35. Failed treatment work stays in the causal denominator

When evaluating whether deploying AI improves business outcomes, failed AI attempts remain part of the treatment experience.

```text
Treatment Conversion
=
Treatment Outcomes
──────────────────
All Eligible Treatment Assignments
```

Removing failed treatment interactions measures the performance of successful AI work, not the effect of deploying the AI workload.

## 36. Accepted Work explains treatment performance; it does not replace the counterfactual

Accepted Work is valuable for diagnosing why a treatment performs well or poorly.

The counterfactual is still required to determine whether the treatment created incremental business value.

## 37. Replace assumptions with observations progressively

Scenario assumptions are useful before real evidence exists.

As pilot evidence becomes available:

```text
Assumption
    ↓
Observed Evidence
    ↓
More credible economics
```

Do not retain an assumption simply because it produces a cleaner value story when better evidence is available.

## 38. Predefine the measurement rules

Eligibility, assignment, attribution windows, exclusions, and primary outcomes should be defined before examining pilot results.

Changing the measurement rules after seeing outcomes weakens the credibility of the evidence.

## 39. Value and cost must share the same economic basis

Economic value and economic cost cannot be combined merely because both are measured in dollars.

They must refer to a compatible:

```text
population
+
time period
+
workload scope
```

For example:

```text
monthly value
-
single-test-run cost
```

does not produce meaningful Net Economic Value.

## 40. Execution cost completeness is not customer-cost completeness

A complete account of runtime execution cost does not automatically include every cost relevant to the customer's economic decision.

```text
Full Execution Cost
≠
Total Relevant Customer Cost
```

Customer Net Economic Value requires the cost boundary appropriate to the decision being made.

## 41. Historical economics do not answer the next-dollar question

A workload can have strong historical economics while the next increment of scale has poor economics.

Investment decisions should evaluate the additional value and additional cost caused by the proposed change.

## 42. Define the increment before calculating incremental economics

"Scale the workload" is not an economic unit.

The proposed change must be explicit, such as:

```text
additional 1,000 interactions/month
new geography
new workflow
higher service level
```

Only then can incremental value and incremental cost be meaningfully compared.

## 43. Sunk cost and incremental cost answer different questions

A cost already incurred may matter to total historical economics without affecting the economics of the next investment.

```text
Would this cost change if we make the proposed investment?
```

is the key incremental-cost question.

## 44. Marginal economics can be nonlinear

Fixed capacity, shared infrastructure, and step-function resource requirements can make the cost of the next unit very different from historical average cost.

```text
Average Cost
≠
Marginal Cost
```

Scale decisions should model the actual cost behavior of the proposed increment.

## 45. Evidence confidence and value resilience are different

Evidence Confidence asks how strongly the current economic claim is supported.

Value Resilience asks how much important conditions can deteriorate before the economic conclusion changes.

A result can be well evidenced but fragile, or weakly evidenced but apparently resilient in scenario analysis.

## 46. Sensitivity analysis tests conclusions, not assumptions

Changing an assumption across scenarios reveals how economics respond to that assumption.

It does not establish which assumption is true.

```text
Sensitivity
≠
Evidence
```

## 47. Break-even boundaries can be more useful than base-case estimates

A base case tells us what economics look like under one set of inputs.

A break-even boundary tells us how far an important driver can deteriorate before the economic conclusion changes.

That margin can be more useful for decision-making than the headline value estimate.

## 48. High uncertainty plus high sensitivity is an evidence priority

The most decision-relevant evidence gaps are often variables that are both:

```text
highly uncertain
+
economically sensitive
```

Those variables should receive priority in pilots, instrumentation, and follow-up analysis.

## 49. Assessment is not scoring

A workload assessment should preserve the important dimensions of evidence rather than averaging them into one universal score.

```text
Strong technical evidence
+
weak business evidence
```

should remain visible as two different facts.

## 50. A failed gate should not disappear inside an average

A composite score can allow strong dimensions to compensate numerically for a decision-critical missing requirement.

Some evidence gaps should remain explicit gates rather than weighted components.

## 51. Synthesis should reuse evidence, not recalculate it

The assessment layer should consume established technical, economic, resilience, and evidence records.

It should not independently recreate their calculations.

This preserves traceability and keeps one source of truth for each claim.

## 52. Decision gates are not scores

Decision gates constrain which actions are supportable.

They should not be averaged into a universal workload score.

## 53. Evidence sufficiency depends on decision consequence

Evidence that is sufficient to justify exploration may be insufficient to justify large-scale investment.

```text
Evidence
+
Decision Context
=
Gate Readiness
```

## 54. Unknown is not failure

A missing assessment should remain Unknown.

```text
UNKNOWN ≠ FAIL
UNKNOWN ≠ PASS
```

The correct response to Unknown is to determine whether the evidence is required for the decision and, if so, how to obtain it.

## 55. Some gates are non-compensable

Mandatory safety, security, regulatory, Responsible AI, or governance requirements cannot be numerically offset by strong economics.

```text
High Value
+
Failed Mandatory Control
≠
Approval
```