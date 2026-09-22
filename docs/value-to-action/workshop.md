# Value-to-Action Workshop

This workshop is designed to be **run**, not read like a textbook.

## Goal

> How do we move from AI consumption to an evidence-backed business action without confusing modeled value with proven value?

```text
MEASURE → PROVE → VALUE → TEST → DECIDE → ACT
```

## Before you start

The current app uses a fixed 10-case regression suite. Treat it as a technical test harness.

It can show model/tool consumption, Accepted Work, execution cost evidence, modeled economics, sensitivity, and decision-state propagation.

It cannot show real customer conversion, real incremental orders, or realized ROI.

## Run

Regression — the fixed technical benchmark:

```bash
uv run scripts/run_evaluation.py
```

Simulation — demonstrates how business/causal evidence flows without pretending it is production evidence:

```bash
uv run scripts/run_simulation.py --seed 42 --outcome-seed 4201 --count 20
```

Dashboard:

```bash
uv run streamlit run apps/value_to_action_dashboard.py
```

Use the dashboard to follow a run through MEASURE → PROVE → VALUE → TEST → DECIDE → ACT.

## Observe

### 1. MEASURE

Look for attempted interactions, Accepted Work, tokens/model cost, tool activity, cost per attempt/Accepted Work, and cost completeness.

Ask: **What is measured directly, and what remains missing?**

```text
response ≠ Accepted Work
model cost ≠ full execution cost ≠ Total Customer Cost
```

### 2. PROVE

Look at business-outcome and pilot evidence. In the current regression environment, downstream fields should remain Unknown.

Ask: **What evidence would we need before saying an order was caused by AI?**

```text
Accepted Work ≠ business outcome ≠ incremental business outcome
```

### 3. VALUE

Current:

```text
scenario assumptions × measured technical behavior → modeled economics
```

Decision-grade target:

```text
incremental economic value - Total Relevant Customer Cost = Customer Net Economic Value
```

For additional investment:

```text
ΔValue - ΔCost = Incremental Net Economic Value
```

### 4. TEST

Ask separately:

- How strongly is this claim supported?
- How far can important conditions deteriorate before the conclusion changes?

```text
Evidence Confidence ≠ Value Resilience
Sensitivity analysis ≠ evidence collection
```

### 5. DECIDE

Gate states:

```text
PASS | CONDITIONAL | FAIL | UNKNOWN | NOT_APPLICABLE
```

Do not average away a mandatory control or decision-critical evidence gap.

### 6. ACT

| Action | Primary reason |
|---|---|
| **Scale** | Attractive established next-dollar economics + required gates |
| **Sustain** | Current operation justified; no material change needed |
| **Optimize** | Execution efficiency/quality is the main constraint |
| **Prove** | Decision-critical evidence is missing and obtainable |
| **Restructure** | Commercial/ownership/funding/control structure is the constraint |
| **Pause** | No justified near-term work or an external blocker |
| **Retire** | No continuing rationale |

For current Contoso, the primary deficit is evidence, so the current action is **PROVE**.

## Participant exercise

Before looking at the action output, answer:

1. What is definitely measured?
2. What is only modeled?
3. What remains Unknown?
4. What evidence gap is most likely to change the decision?
5. What action addresses that gap?

## What not to conclude

Do not say:

- “The agent has ~100× ROI.”
- “Orders after AI are recovered orders.”
- “No observed order means no order occurred.”
- “A successful regression proves production value.”
- “A high modeled value means we should scale.”

Prefer:

- “The scenario model shows a potentially large opportunity relative to model inference cost.”
- “Business outcomes and incrementality remain unproven.”
- “The next justified step is evidence collection.”
