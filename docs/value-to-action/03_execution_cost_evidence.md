# Execution Cost Evidence Inventory — v1

## Decision Question

Which components of the Contoso execution boundary can we economically observe today, and where are the remaining evidence gaps?

## Evidence Status

| Component | Status | Current Evidence | Remaining Gap |
|---|---|---|---|
| Model inference | Measured | model identity, input/output/cached/reasoning/total tokens, model cost | — |
| Accepted Work | Measured | attempted, evaluated, accepted/rejected interactions | broader production evidence |
| Azure AI Search/tool execution | Measured | per-interaction tool-call count and tool type from Responses output | monetary attribution |
| Repeated tool calls | Measured | multiple tool calls are preserved per interaction | distinguish retry vs intentional additional retrieval if needed |
| End-to-end invocation latency | Measured | client-observed `latency_ms` per interaction | component-level latency attribution |
| Agent/version identity | Measured | agent name and version | — |
| Response identity | Measured | response ID | — |
| Run/workload identity | Measured | run ID, workload ID, interaction ID | — |
| Retry/recovery activity | Partially observable | repeated execution can be observed | explicit retry/recovery classification |
| Azure AI Search cost | Unpriced / unallocated | Search usage is measured | pricing model/SKU + allocation rule |
| Foundry agent runtime | Known treatment | runtime component is identified | economic treatment handled in cost attribution |
| Observability | Allocated / Unknown | telemetry capability exists | workload allocation rule |
| Human review/escalation | Unknown | no production human process measured | intervention rate, time, and cost |
| Failure recovery | Unknown | no production recovery process measured | recovery process + economic cost |
| Evaluation/judge cost | Lifecycle | evaluation runs are observable | lifecycle-cost attribution if required |
| CI/CD / implementation | Lifecycle | project activity exists | attribution if relevant to the decision |

## Minimal Execution Record

Each evaluated interaction now preserves an evidence record containing:

```text
Workload ID
Run ID
Interaction ID
Case / category
Agent name + version
Response ID
Model
Token consumption
Model cost
Latency
Tool-call count + types
Accepted / rejected
```

This creates a traceable link between:

```text
AI Consumption
      ↓
System Execution
      ↓
Accepted Work
```

## Evidence Lifecycle

Execution evidence and outcome evidence are produced at different stages.

```text
Execute interaction
      ↓
Capture execution evidence
      ↓
accepted = Unknown
      ↓
Run evaluation
      ↓
Determine Accepted Work
      ↓
Join by stable interaction identity
      ↓
Final Execution Record
```

The join uses a stable interaction identifier rather than positional ordering.

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

For example:

```text
2 Azure AI Search calls
```

is measured execution evidence.

It does **not** automatically mean:

```text
2 × $X Search cost
```

until the pricing and allocation model is established.

## What We Can State Today

We can directly observe:

- how many interactions were attempted,
- how much model consumption each interaction used,
- model inference cost,
- how many Search/tool calls occurred,
- which tool types were invoked,
- client-observed end-to-end latency,
- which interactions became Accepted Work.

We cannot yet claim complete execution economics because several economically relevant components remain unpriced or unallocated.

## Current Cost Layers

```text
Measured and priced
───────────────────
Model inference cost
        ↓
Known Direct Cost / Accepted Work


Measured but not yet priced
───────────────────────────
Azure AI Search activity


Not yet economically attributed
───────────────────────────────
Shared infrastructure
Observability
Human intervention
Failure recovery
        ↓
Full Execution Cost / Accepted Work
        remains unestablished
```

## Important Observation

More AI activity does not necessarily produce more useful work.

An interaction can consume:

```text
tokens
+ tool calls
+ latency
```

and still fail the Accepted Work boundary.

Therefore:

```text
Consumption ≠ Useful Progress
```

Rejected executions remain economically relevant because their resource consumption does not disappear.

## Key Takeaways

- Execution evidence should be captured per interaction, not only as run-level averages.
- Tool usage should be measured rather than inferred from agent configuration.
- A measured zero is different from missing evidence.
- Execution telemetry and Accepted Work evidence may originate at different stages and should be joined explicitly.
- Resource activity is not automatically monetary cost.
- Unknown or unallocated economics should remain visible rather than being treated as zero.
- Failed executions still consume resources and therefore affect the economics of Accepted Work.

## Next Step

Apply explicit cost-attribution rules to the measured execution evidence and report only the economic metrics that the available evidence can support.