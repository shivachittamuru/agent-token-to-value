# System Boundary — v1

## Decision Question

What complete system is required to produce one Accepted Work Unit, and which costs belong in its economics?

## Production Execution Path

```text
Customer Inquiry
      ↓
Foundry Prompt Agent / Orchestration
      ↓
GPT Model Call(s)
      ↓
Azure AI Search / Tool Call(s)
      ↓
Retrieved Context
      ↓
Final Response
      ↓
Accepted Work
```

Retries and additional model/tool calls required to complete the interaction remain inside the execution boundary.

## Two Boundaries to Keep Separate

### Technical Execution Boundary

Everything that participates in producing the customer response.

### Economic Cost Boundary

The resources whose cost should be attributed to producing and operating Accepted Work.

These boundaries overlap, but they are not identical.

For example, regression evaluators and judge-model calls generate real cost, but they are not normally executed for every production customer interaction.

## Production Execution Scope

### Inside the Runtime Boundary

- Foundry agent/orchestration
- model calls
- Azure AI Search/tool calls
- retrieved context
- repeated calls required by the interaction
- operational telemetry required to run the workload
- required human review or escalation, if introduced

### Outside Direct Per-Interaction Runtime Cost

- regression evaluation runs
- judge-model calls
- CI/CD
- developer experimentation
- one-time implementation/setup
- workshop/demo development

Outside the direct runtime boundary does **not** mean economically irrelevant.

These costs belong to lifecycle, governance, implementation, or total-customer-cost analysis instead.

## Cost Categories

| Category | Examples | Economic Treatment |
|---|---|---|
| Direct execution | model inference, tool execution, retries | Attribute to workload execution |
| Allocated operating | Search capacity, runtime infrastructure, observability | Allocate when required to operate the workload |
| Human / recovery | review, escalation, correction, recovery | Include when required or caused by the workload |
| Lifecycle / evidence | evaluation judges, regression testing, CI/CD | Track separately from normal production execution |
| Implementation | engineering, setup, integration | Relevant to total customer economics, not runtime unit cost |

Required human controls are system costs; they are not automatically waste.

## Cost Behavior

Costs may behave differently as workload volume changes:

- **Variable** — increases with workload usage
- **Fixed / committed** — incurred even when usage changes
- **Shared** — supports multiple workloads and requires allocation
- **Step-function** — remains flat until additional capacity is required

Therefore:

```text
Average allocated cost
≠
Marginal cost of one additional interaction
```

This distinction becomes important when deciding whether the workload should scale.

## Failure Boundary

Failure can create several different economic effects:

```text
Failure
 ├─ Wasted execution
 │    resources consumed without Accepted Work
 │
 ├─ Recovery / rework
 │    retries, escalation, human correction
 │
 └─ Business consequence
      lost customer, incorrect action, service recovery, risk
```

Wasted execution and recovery belong close to execution economics.

Business consequences belong later in the value/risk analysis.

Do not combine them prematurely or count the same loss twice.

## Cost Layers

Keep different economic questions separate:

```text
Model Cost
    ↓
Full Execution Cost
    ↓
Total Customer Cost
```

### Model Cost

Cost of model inference.

### Full Execution Cost

Cost of the complete operating system required to produce Accepted Work.

### Total Customer Cost

Broader cost of obtaining the business outcome, potentially including operations, required human effort, governance, and implementation.

Do not collapse these into one number.

## Current Boundary Evidence

### Known Inside the Execution Path

- Foundry prompt-agent execution
- GPT model usage
- Azure AI Search/tool execution
- response generation
- Accepted Work determination

### Economically Incomplete

- Search cost attribution
- shared runtime/platform cost
- observability allocation
- human review/escalation
- recovery cost
- lifecycle cost allocation

Unknown costs should remain visible rather than being silently treated as zero.

## Key Takeaways

- The model call is not the economic system.
- The economic unit is the complete system required to produce Accepted Work.
- Technical execution boundary and economic cost boundary are related but different.
- Direct, shared, lifecycle, implementation, and human costs should not be mixed blindly.
- Fixed, variable, shared, and step-function costs behave differently.
- Evaluation cost is real but is not automatically a production cost per interaction.
- Failure can create execution, recovery, and downstream business costs.
- Unknown economically relevant components should remain Unknown until evidence or an explicit allocation rule exists.

## Next Step

Inventory the actual Contoso execution evidence and classify each economically relevant component by what is measured, derivable, allocated, or still Unknown.