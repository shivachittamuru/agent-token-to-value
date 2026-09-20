# Cost Attribution Rules — v1

## Decision Question

How should observed resource usage be converted into economic cost for this workload?

## Core Rule

```text
Observed Resource Use
        +
Pricing / Allocation Rule
        +
Decision Context
        ↓
Attributed Cost
```

Resource telemetry alone is not economic cost.

## Attribution Modes

| Mode | Meaning |
|---|---|
| Direct | Cost can be tied directly to one interaction |
| Usage-derived | Measured usage can be priced using a known rate |
| Allocated | Shared or committed cost requires an allocation rule |
| Unknown | Cost is relevant, but evidence is insufficient |

## Cost Behavior

Costs may behave differently as workload volume changes:

- **Variable** — increases with usage
- **Fixed / committed** — incurred even when usage changes
- **Shared** — supports multiple workloads and requires allocation
- **Step-function** — stays flat until additional capacity is required

A cost can belong to one attribution mode and have a different cost behavior.

Example:

```text
Azure AI Search
→ usage may be observable
→ cost may still be fixed/shared/step-function
→ tool-call count alone does not establish dollar cost
```

## Contoso v1 Attribution

| Component | Attribution | Cost Behavior | Current Treatment |
|---|---|---|---|
| Model inference | Direct | Variable | Measured and priced |
| Azure AI Search | Pending pricing model | Unknown until SKU/model is known | Usage measured; cost remains unpriced |
| Foundry native prompt-agent runtime | Direct | No separate runtime fee | Known zero additional agent-runtime fee; separately billed model/tool costs still apply |
| Retries / repeated model calls | Direct | Variable | Attribute actual additional execution |
| Observability | Allocated | Shared / fixed | Include only with a defensible workload allocation |
| Human review | Direct / allocated | Variable or policy-driven | Include when observed |
| Failure recovery | Direct | Variable | Include actual retry, rework, or escalation |
| Evaluation / judge runs | Lifecycle | Variable by evaluation activity | Keep separate from production execution |
| CI/CD | Lifecycle / allocated | Shared | Track separately when material |
| Implementation effort | Implementation | Fixed / sunk / amortized | Not part of per-interaction runtime cost |

## Average vs Incremental Cost

These answer different decisions.

### Average Execution Cost

```text
Total Attributed Execution Cost
───────────────────────────────
Accepted Work Units
```

Useful for:

> Is this workload economically healthy overall?

### Incremental Execution Cost

```text
Additional Cost Caused by More Workload
───────────────────────────────────────
Additional Accepted Work
```

Useful for:

> Has this workload earned the right to consume more resources?

A workload can have:

```text
high average cost
+
low incremental cost
```

or the reverse.

Do not treat them as interchangeable.

## Known Zero vs Unknown

These are different economic states.

```text
$0
=
evidence supports no additional attributed cost

None / Unknown
=
the component matters, but cost evidence is incomplete
```

Do not convert Unknown into zero for convenience.

## Failure Cost

Failure can create several different economic effects:

```text
Failure
 ├─ wasted execution
 │    model/tool resources consumed without Accepted Work
 │
 ├─ recovery / rework
 │    retries, escalation, human correction
 │
 └─ business consequence
      lost customer, incorrect action, service recovery, risk
```

Keep these distinct so the same loss is not counted twice.

Wasted execution and recovery belong close to execution economics.

Business consequences belong later in the value/risk analysis.

## What Not to Monetize Automatically

Do not assign dollar values merely because a metric is observable.

Examples:

```text
Latency ≠ economic loss
Tool-call count ≠ tool cost
Human touch ≠ labor cost
Retry count ≠ business loss
```

A defensible causal bridge is required.

For example:

```text
Latency
→ lower conversion / SLA penalty / operator delay
→ evidenced economic effect
```

Only then should it become economic value or cost.

## Cost Completeness

A cost number should carry its completeness state.

Example:

```text
Known Direct Execution Cost = $0.007
Cost Completeness = Partial
```

is more accurate than:

```text
Execution Cost = $0.007
```

when economically relevant components remain unallocated or Unknown.

## Guardrails

- Do not convert measured activity into dollars without a valid pricing or allocation rule.
- Do not treat Unknown as zero.
- Do not treat fixed cost as irrelevant.
- Do not confuse average cost with incremental cost.
- Do not include lifecycle or implementation costs in per-interaction runtime cost unless the decision requires it.
- Do not double-count the same resource across categories.
- Do not label partial cost as full or total execution cost.
- Keep allocation rules visible so others can understand how the number was produced.

## Key Takeaway

The goal is not to create the largest possible cost model.

The goal is to include the right costs for the decision being made while preserving what is:

- measured,
- directly priced,
- allocated,
- assumed,
- or still Unknown.

## Next Step

Apply these rules to the actual Contoso execution records and report only the execution-economic metrics that are defensible today.