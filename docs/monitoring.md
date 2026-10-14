---
title: Monitoring Microsoft Foundry Agents
description: Implementation reference for Foundry agent operations and quality monitoring.
---

## Monitoring Microsoft Foundry Agents

> Implementation reference. See the [README](../README.md) and
> [architecture overview](architecture.md) for the current framework.

## Purpose

Evaluation answers:

> **Is the agent good?**

Monitoring answers:

> **Is the deployed agent still healthy and trustworthy right now?**

A production agent has two different kinds of health.

```text
Operational health
------------------
Latency
Errors
Run success
Token usage
Traffic

AI quality
----------
Correctness
Task adherence
Grounding
Abstention
Hallucination
Safety
```

You need both.

An agent that is correct but takes 40 seconds to respond is unhealthy.

An agent that responds in one second but invents facts is also unhealthy.

---

## 1. Agent Monitoring Dashboard

Microsoft Foundry provides an Agent Monitoring Dashboard backed by the project's connected Application Insights resource.

Typical dashboard signals include:

- token usage
- latency
- run success rate
- evaluation metrics
- red-team results when configured

Monitoring data retention and billing follow the connected Application Insights configuration.

The dashboard is therefore both:

```text
Agent quality dashboard
        +
Operational observability dashboard
```

---

## 2. Operational monitoring

### Token usage

Track how many tokens agent traffic consumes.

High usage can indicate:

- unnecessarily long system instructions
- excessive context
- verbose answers
- repeated tool/model loops
- inefficient retrieval

Token monitoring matters because quality improvements sometimes increase cost.

Always consider:

```text
quality
vs
latency
vs
token usage
vs
cost
```

### Latency

Latency measures how long agent runs take.

Potential causes of high latency include:

- model throttling
- slow external tools
- multiple tool calls
- network latency
- large prompts
- repeated reasoning loops

Inspect latency together with traces rather than treating the number alone as root cause.

### Run success rate

Run success rate measures how often agent runs complete successfully.

Failures may come from:

- model errors
- tool errors
- authentication
- throttling
- network failures
- bad tool inputs
- runtime exceptions

A high-quality agent still needs reliable execution.

---

## 3. Traces

Traces answer:

> **What exactly happened during this run?**

A typical agent trace may look like:

```text
User request
    ↓
Model call
    ↓
Tool decision
    ↓
Azure AI Search
    ↓
Tool result
    ↓
Model call
    ↓
Final response
```

Useful trace questions:

- Did the agent call the expected tool?
- What query did it send?
- Did the tool return useful evidence?
- Did the model use the evidence correctly?
- Were there retries?
- Where was latency introduced?
- Did the run fail?
- Was the final answer supported?

Tracing helps separate:

```text
retrieval failure
reasoning failure
behavior failure
tool/runtime failure
```

---

## 4. Continuous evaluation

Continuous evaluation evaluates **sampled production responses**.

```text
Real agent traffic
       ↓
sample some percentage
       ↓
run evaluators
       ↓
quality metrics over time
```

This answers:

> **How is the agent behaving on real user traffic?**

Foundry Monitor settings allow you to:

- enable continuous evaluation
- choose evaluators
- set a sample rate

The project managed identity needs the required Foundry permissions for continuous evaluation rules.

---

## 5. Why sampling matters

LLM-based evaluation costs money.

One production request can become:

```text
User request
    ↓
Agent model/tool calls
    ↓
Response

PLUS

Judge-model call
    ↓
Evaluation score
```

At large scale, evaluating 100% of traffic may be unnecessary.

Choose sample rate based on:

- traffic volume
- business risk
- evaluation cost
- change frequency
- quality sensitivity

Examples:

```text
Low-volume high-risk agent
→ evaluate a larger share

Very high-volume low-risk assistant
→ evaluate a representative sample
```

---

## 6. Continuous evaluation vs scheduled evaluation

These solve different problems.

### Continuous evaluation

Uses real production traffic.

```text
Users
  ↓
Agent
  ↓
Sampled responses
  ↓
Evaluators
```

Question answered:

> What unexpected behaviors are real users discovering?

### Scheduled evaluation

Uses a fixed benchmark.

```text
Schedule
   ↓
Known regression dataset
   ↓
Current agent
   ↓
Evaluators
```

Question answered:

> Did something break behavior we already knew should work?

A mature system uses both.

---

## 7. Production feedback loop

The most valuable monitoring loop is:

```text
Production traffic
      ↓
Continuous evaluation
      ↓
Low-quality case
      ↓
Inspect trace
      ↓
Identify root cause
      ↓
Fix prompt/tool/model
      ↓
Add failure to regression dataset
      ↓
Never silently regress again
```

Traces are not just logs. They are a source of future test cases.

---

## 8. Alerts

Foundry Monitor supports alerting capabilities for conditions such as:

- latency
- token usage
- evaluation scores
- red-team findings

Some monitoring alert capabilities are currently preview.

The desired enterprise loop is:

```text
Metric crosses threshold
       ↓
Alert
       ↓
Engineer inspects traces
       ↓
Root cause
       ↓
Fix
       ↓
Regression case added
```

Alerts should point to an actionable investigation, not generate noise.

---

## 9. Red-team monitoring

Foundry supports scheduled red-team scans as a preview capability.

Red-team testing explores adversarial behaviors such as:

- jailbreaks
- data leakage
- prohibited actions
- unsafe responses
- security weaknesses

This complements quality evaluation.

```text
Quality evaluation
→ Does the agent do the desired task well?

Red teaming
→ Can an adversarial user make it behave dangerously?
```

---

## 10. Monitoring failures by layer

When a monitor or evaluator flags a problem, classify it before changing the prompt.

### Retrieval failure

```text
Needed evidence was not retrieved.
```

Investigate:

- index quality
- search query
- retrieval settings
- data freshness
- tool configuration

### Reasoning failure

```text
Correct evidence was present but interpreted incorrectly.
```

Investigate:

- model
- instructions
- arithmetic
- synthesis logic
- deterministic checks

### Behavior failure

```text
Agent ignored a product rule.
```

Examples:

- answered off-topic question
- invented missing information
- ignored user budget
- failed to abstain

Investigate:

- system instructions
- rubric
- guardrails
- workflow/control logic

### Operational failure

```text
Agent could not execute successfully.
```

Investigate:

- authentication
- tool errors
- service throttling
- network
- runtime
- permissions

Do not automatically treat every bad output as a prompt problem.

---

## 11. Monitoring and Application Insights

Foundry monitoring data is stored in the project's connected Application Insights resource.

This enables deeper operational analysis and retention beyond the high-level portal dashboard.

Depending on your setup, access to traces and logs may require Azure RBAC roles on Application Insights or Log Analytics.

A useful mental model:

```text
Foundry Monitor
    ↓
High-level agent experience

Application Insights / Log Analytics
    ↓
Deeper telemetry and investigation
```

---

## 12. Monitoring custom or externally hosted agents

Monitoring philosophy does not require the agent runtime itself to be Foundry-managed.

Microsoft documents a pattern for registering/onboarding custom agents and sending OpenTelemetry-compliant traces to the same Application Insights resource.

```text
Prompt Agent ─────┐
Hosted Agent ─────┼→ Foundry / App Insights observability
Custom Agent ─────┘
```

---

## 13. Recommended monitoring setup for a small agent

For a narrow learning project such as the Contoso Coffee agent:

### Start with

- Agent Monitoring Dashboard
- Application Insights connection
- continuous evaluation with a modest sample
- one strong custom behavior evaluator
- latency
- token usage
- run success rate

### Add later

- scheduled regression evaluation
- alerts
- red-team scans
- production-trace mining
- CI/CD gates

Do not configure every feature simply because it exists. Each monitor should answer a real engineering question.

---

## 14. Production monitoring maturity model

```text
Level 1 — Manual trace inspection
"What happened in this run?"

Level 2 — Operational dashboard
"Are latency/errors/tokens healthy?"

Level 3 — Continuous evaluation
"Is real traffic still high quality?"

Level 4 — Alerts
"Tell me when important metrics degrade."

Level 5 — Trace mining
"What new failures should enter the regression suite?"

Level 6 — Scheduled regression
"Are known requirements still stable?"

Level 7 — Automated release gates
"Can regressions be prevented from shipping?"
```

---

## Architecture Journal

### What Foundry automates

- agent telemetry collection
- monitoring dashboard
- Application Insights integration
- continuous evaluation
- sample-rate configuration
- scheduled evaluation
- alerts
- red-team scan scheduling

### What we still own

- which metrics matter
- what thresholds are meaningful
- evaluator quality
- sampling strategy
- root-cause analysis
- deciding when an alert requires action
- converting production failures into regression cases

### What changes with LangGraph?

The monitoring philosophy stays the same.

LangGraph gives more control over internal orchestration, but production still requires:

- OpenTelemetry/traces
- latency/error monitoring
- evaluation of sampled traffic
- alerting
- regression dataset growth
- quality gates

Observability and evaluation are **agent-framework-independent disciplines**.

---

## References

- [Monitor agents with the Agent Monitoring Dashboard](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/how-to-monitor-agents-dashboard)
- [Cloud evaluation with the Microsoft Foundry SDK](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/cloud-evaluation)
