# Value-to-Action

A compact framework for moving from **AI consumption** to an **evidence-backed business action**.

```text
MEASURE → PROVE → VALUE → TEST → DECIDE → ACT
```

The framework separates what is **measured**, **modeled**, **observed**, **incremental**, and **unknown** so a large-looking value estimate cannot silently become a scale recommendation.

## The six questions

1. **Measure** — what did AI consume and what useful work did it produce? Count work only when it passes the required quality/control floor: **Accepted Work**.
2. **Prove** — did anything change in the business? Accepted Work is not Business Value; causal claims need a credible counterfactual.
3. **Value** — what was that change worth and what did it cost? Keep modeled value separate from evidence-backed incremental value.
4. **Test** — how much should we believe the economics, and how easily do they break? Keep Evidence Confidence separate from Value Resilience.
5. **Decide** — which actions are supportable? Use independent gates, not a composite score.
6. **Act** — what should happen next? Choose **Scale, Sustain, Optimize, Prove, Restructure, Pause, or Retire** based on the primary deficit.

## Contoso end-to-end

**Workload:** AI-assisted handling of otherwise-unanswered, AI-eligible Contoso Coffee menu inquiries when staff cannot respond.

### Measure

```text
Inquiry → Agent / model / tools → Response → Quality + scope verification → Accepted Work
```

The project measures tokens, model cost, tool activity, latency, and Accepted Work. Failed work still consumes resources.

### Prove

```text
Accepted Work → customer stays engaged → order completed → incremental order recovered
```

The current regression run does **not** observe those business outcomes. A real pilot would need stable interaction identity, treatment/control assignment, downstream order evidence, and a predefined attribution window.

### Value

The current scenario model estimates:

```text
missed demand × AI-eligible share × AI success × conversion × order value × contribution margin
= modeled recovered contribution
```

This supports a **Modeled AI Value Multiple**:

```text
modeled recovered contribution / measured model inference cost
```

It is useful for opportunity sizing. It is **not realized ROI**.

Stronger economics require:

```text
incremental contribution - Total Relevant Customer Cost = Customer Net Economic Value
```

For an expansion decision:

```text
additional value - additional customer cost = Incremental Net Economic Value
```

### Test

```text
Evidence Confidence = how strongly is the claim supported?
Value Resilience     = how easily does the conclusion break?
```

Sensitivity tests the model; it does not prove the assumptions.

### Decide

Current Contoso state:

```text
Technical performance   established in regression
Execution cost          partial
Business outcomes       unknown
Incrementality          unknown
Economic value          modeled only
Next-dollar economics   not established
Resilience              modeled scenario / not classified
```

Decision gates constrain the action space. A high modeled value cannot override missing causal evidence or a failed mandatory control.

### Act

```text
Evidence deficit   → PROVE
Execution deficit  → OPTIMIZE
Structural deficit → RESTRUCTURE
Strong next-$ case + required gates → SCALE
```

For the current Contoso evidence state, the primary deficit is **evidence**, so the present action is **PROVE** through a bounded real-world pilot.

## Current evidence boundary

The app repeatedly runs a fixed 10-case regression suite. That is useful for technical comparability, but it does not create real business evidence.

```text
Measured regression evidence ≠ production business evidence
Modeled economics            ≠ realized value
Observed order               ≠ incremental order
Unknown                      ≠ zero or failure
```

Simulation mode makes the evidence pipeline dynamic for teaching and dashboarding. Synthetic outcomes are always explicitly labeled **simulated** and never treated as production evidence.

## Two evidence modes

Both modes use **real** agent execution and **real** technical evaluation. They differ only in the downstream business evidence.

```text
REGRESSION
  fixed benchmark
+ real AI execution / evaluation
+ downstream business evidence Unknown

SIMULATION
  seeded synthetic inquiries
+ real AI execution / evaluation
+ synthetic treatment / control
+ synthetic business outcomes / economics
+ explicit simulation provenance
```

> Simulation evidence can **establish a claim within simulation scope**. It never satisfies a production evidence requirement — real business outcomes, production incrementality, and complete customer cost stay Unknown, so the action stays **PROVE**.

## Dashboard

```bash
uv run streamlit run apps/value_to_action_dashboard.py
```

The dashboard presents a run through **MEASURE → PROVE → VALUE → TEST → DECIDE → ACT**.

## Where to go next

- [workshop.md](workshop.md) — what to run, observe, and discuss.
- [evidence-model.md](evidence-model.md) — compact technical reference.
- [economic_reasoning_principles.md](economic_reasoning_principles.md) — memorable reasoning rules.
