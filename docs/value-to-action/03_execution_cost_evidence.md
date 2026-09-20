# Execution Cost Evidence Inventory — v1

## Decision Question
Which components of the Contoso execution boundary can we economically measure today, and where are the evidence gaps?

## Evidence Status

| Component | Status | Current Evidence | Gap |
|---|---|---|---|
| Model inference | Measured | model + token usage + inference cost | — |
| Accepted Work | Measured | attempted, evaluated, accepted interactions | broader production evidence |
| Azure AI Search/tool execution | Derivable | tool calls visible in traces | not captured in current economics run |
| Repeated tool/model calls | Derivable | execution trajectory can expose them | no run-level aggregation |
| Retry/recovery activity | Unknown | — | explicit retry/recovery evidence |
| Agent/runtime cost | Unknown | runtime is used | workload-attributed cost |
| Search service cost | Allocated / Unknown | shared service dependency | capacity/pricing + allocation rule |
| Latency | Derivable | execution timing can be instrumented | not currently persisted |
| Observability | Allocated | platform capability exists | workload allocation |
| Human review/escalation | Unknown | none currently measured | rate + cost |
| Failure recovery | Unknown | — | recovery process + cost |
| Evaluation/judge cost | Lifecycle | evaluation runs occur | optional lifecycle-cost accounting |
| CI/CD / implementation | Lifecycle | project infrastructure exists | attribution if decision requires it |

## Evidence Rule

```text
Observed resource use
        ≠
Economic cost

Resource telemetry
        +
Pricing / allocation rule
        ↓
Economic attribution
```

## Current Cost Layers

```text
Measured today
──────────────
Model inference cost
        ↓
Cost / Accepted Work

Not yet complete
────────────────
+ Tool execution
+ Runtime/platform
+ Allocated infrastructure
+ Recovery/human cost
        ↓
Full Execution Cost / Accepted Work
```