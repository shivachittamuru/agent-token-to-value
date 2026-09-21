# Evidence Model

Compact technical reference for the Value-to-Action evidence contracts.

```text
Consumption → AI Work → Accepted Work → Business Outcome → Incremental Outcome
→ Economic Value → Evidence Confidence + Value Resilience → Decision Gates → Portfolio Action
```

## Core layers

| Layer | Question | Current Contoso state |
|---|---|---|
| Execution | What resources/actions produced the response? | Measured; cost partial |
| Accepted Work | Did the response satisfy task + mandatory quality/control floors? | Measured in regression |
| Business Outcome | What happened after the AI interaction? | Unknown |
| Pilot / Counterfactual | What would have happened without AI? | Unknown |
| Economic Value | What is the attributable outcome worth? | Modeled only |
| Incremental Economics | Is the next investment worth its additional cost? | Not established |
| Resilience | How sensitive is the economic conclusion? | Modeled scenario |
| Assessment | What is established, modeled, partial, or Unknown? | Evidence incomplete |
| Decision | Which actions are supportable? | Scale constrained |
| Action | What should happen next? | PROVE |

## Accepted Work

```text
task success + mandatory guardrails = Accepted Work
```

A completed response is not automatically useful work. Failed work remains in the consumption numerator.

## Execution Cost

Keep three boundaries distinct:

```text
Model Cost → Full Execution Cost → Total Relevant Customer Cost
```

A precise partial number is still partial.

## Business Outcome

```text
Accepted Work → customer continues → order completed
```

Missing downstream evidence remains Unknown, not False. Stable interaction identity allows business evidence to arrive later than technical telemetry.

## Pilot / Counterfactual

```text
order after AI ≠ order caused by AI
```

Preferred shape:

```text
Eligible inquiry → Assignment → Treatment / Control → Outcomes → Compare
```

Assignment is defined before AI success. Failed treatment interactions stay in the treatment denominator.

## Economic Value

Modeled:

```text
modeled recovered contribution / measured model inference cost = Modeled AI Value Multiple
```

Evidence-backed:

```text
treatment outcome - counterfactual outcome = incremental outcome
```

Decision-grade:

```text
incremental economic value - Total Relevant Customer Cost = Customer Net Economic Value
```

Value and cost must share the same population, period, and workload scope.

## Incremental / next-dollar economics

```text
additional value caused by the change - additional customer cost caused by the change
= Incremental Net Economic Value
```

Historical average economics do not answer the next-dollar question.

## Evidence Confidence and Value Resilience

**Evidence Confidence:** how directly, completely, representatively, and causally is the claim supported?

**Value Resilience:** how much can important conditions deteriorate before the conclusion changes?

Sensitivity tests the model. It does not prove assumptions.

## Decision Gates

Gate states:

```text
PASS | CONDITIONAL | FAIL | UNKNOWN | NOT_APPLICABLE
```

Typical gates: strategic/mandatory, value, evidence, resilience, incremental economics, commercial fit, and Responsible AI/risk/control.

Mandatory safety, security, regulatory, or governance failures are non-compensable.

## Portfolio Action

```text
Evidence deficit   → PROVE
Execution deficit  → OPTIMIZE
Structural deficit → RESTRUCTURE
Strong incremental case + required gates → SCALE
```

Sustain, Pause, and Retire are also valid. Every action needs a reassessment trigger.

## Evidence states

| State | Meaning |
|---|---|
| **Measured** | Direct technical/system evidence exists |
| **Modeled** | Materially derived from assumptions |
| **Observed** | A real downstream event was observed |
| **Incremental / causal** | A defensible counterfactual supports attribution |
| **Unknown** | Required evidence does not exist |
| **Zero** | Evidence supports a value of zero |
| **Not applicable** | The component does not belong to this workload/decision |

```text
Unknown ≠ Zero ≠ False ≠ Not Applicable
```

## Implementation map

| Module | Responsibility |
|---|---|
| `execution.py` | execution evidence and cost attribution |
| `business_outcomes.py` | downstream outcome evidence |
| `pilot_evidence.py` | experiment / counterfactual context |
| `business_economics.py` | scenario economics |
| `economic_value.py` | value evidence contract |
| `incremental_economics.py` | next-dollar economics |
| `value_resilience.py` | sensitivity / break-even |
| `workload_assessment.py` | evidence synthesis |
| `decision_gates.py` | gate readiness and action eligibility |
| `portfolio_action.py` | action selection and reassessment |

The current JSONL files are implementation artifacts created while the contracts were developed. They are not required participant reading.
