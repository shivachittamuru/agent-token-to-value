---
title: Automate Agent Evaluation
description: Implementation reference for scheduled evaluation and CI quality gates.
---

## AUTOMATE — Scheduled Regression + CI/CD Gates

> Implementation reference. See the [README](../README.md) and
> [architecture overview](architecture.md) for the current framework.

## Purpose

This step moves the Prompt Agent lifecycle from **manual evaluation** to **automated regression protection**.

The goal is not to build a large DevOps system. The goal is to make sure important agent behaviors are checked automatically and that regressions can block changes before they reach production.

```text
Known regression suite
        ↓
Automated evaluation
        ↓
Quality thresholds
        ↓
PASS → change can proceed
FAIL → investigate before merge/deploy
```

For this project, automation has two complementary parts:

1. **Scheduled regression evaluation in Microsoft Foundry**
2. **CI/CD regression gating in GitHub Actions**

---

## 1. Scheduled Regression Evaluation

A scheduled evaluation periodically reruns a known evaluation suite against the current agent.

This answers:

> Did something change over time that broke behavior we already know should work?

Example:

```text
Every week
   ↓
Run curated Contoso evaluation dataset
   ↓
Invoke current Prompt Agent version
   ↓
Run custom evaluators
   ↓
Store results in Foundry
   ↓
Review quality trends
```

Possible causes of regression include prompt edits, model changes, Azure AI Search index changes, tool changes, runtime changes, or evaluator changes.

For this project, a weekly schedule is sufficient.

Recommended evaluators:

- `contoso_behavior_rubric`
- `contoso_scope_adherence`

---

## 2. CI/CD Regression Evaluation

Scheduled evaluation protects the deployed agent over time.

CI/CD evaluation protects **changes before they are accepted**.

```text
Developer opens pull request
        ↓
GitHub Actions starts
        ↓
Authenticate to Azure
        ↓
Install locked Python environment
        ↓
Run scripts/run_evaluation.py
        ↓
Invoke persisted Foundry Prompt Agent
        ↓
Evaluate contoso_agent_eval_v3.jsonl
        ↓
Check quality thresholds
        ↓
PASS                       FAIL
 ↓                           ↓
PR can proceed          Workflow fails
                            ↓
                    Investigate in Foundry
```

---

## 3. Why We Own the Evaluation Harness

The first experiment used:

```text
microsoft/ai-agent-evals@v3-beta
```

That proved the GitHub-to-Foundry integration, but it also exposed an important trade-off:

```text
Managed GitHub Action
        ↓
Less code
        ↓
Less control over dependencies and implementation
```

The preferred project shape is therefore:

```text
GitHub Actions
    ↓
our scripts/run_evaluation.py
    ↓
our dataset
    ↓
Foundry APIs
    ↓
Foundry Prompt Agent + Evaluators
```

This gives us control over:

- dependency versions
- dataset selection
- agent invocation
- evaluator selection
- quality thresholds
- failure behavior
- run naming
- result logging

Foundry still provides the managed agent runtime, evaluator execution, persistence, and portal analysis.

---

## 4. GitHub Actions Mental Model

GitHub Actions is simply:

> A temporary remote computer that executes a YAML recipe when an event occurs.

For this project:

```text
Checkout repository
        ↓
Authenticate to Azure
        ↓
Install uv
        ↓
Install Python
        ↓
uv sync --locked
        ↓
uv run --locked scripts/run_evaluation.py
```

Example workflow:

```yaml
name: Agent Regression Evaluation

on:
  workflow_dispatch:
  pull_request:
    branches:
      - main
    paths:
      - "src/**"
      - "evals/**"
      - "scripts/**"
      - ".github/workflows/agent-eval.yml"

permissions:
  id-token: write
  contents: read

jobs:
  evaluate-agent:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    env:
      FOUNDRY_PROJECT_ENDPOINT: ${{ vars.FOUNDRY_PROJECT_ENDPOINT }}
      FOUNDRY_AGENT_NAME: ${{ vars.FOUNDRY_AGENT_NAME }}
      FOUNDRY_AGENT_VERSION: ${{ vars.FOUNDRY_AGENT_VERSION }}
      FOUNDRY_JUDGE_MODEL: ${{ vars.FOUNDRY_JUDGE_MODEL }}
      BEHAVIOR_PASS_RATE_THRESHOLD: ${{ vars.BEHAVIOR_PASS_RATE_THRESHOLD }}
      SCOPE_PASS_RATE_THRESHOLD: ${{ vars.SCOPE_PASS_RATE_THRESHOLD }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Login to Azure
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: Install Python
        run: uv python install

      - name: Sync dependencies
        run: uv sync --locked

      - name: Run agent regression evaluation
        run: uv run --locked scripts/run_evaluation.py
```

---

## 5. GitHub OIDC and Federated Identity

The workflow needs permission to call Azure and Foundry.

We avoid storing a long-lived Azure client secret in GitHub.

Instead, GitHub uses **OpenID Connect (OIDC)** workload identity federation:

```text
GitHub Actions
      ↓
GitHub issues short-lived OIDC token
      ↓
Microsoft Entra ID checks federated credential
      ↓
Token identity matches trusted repo/branch
      ↓
Entra issues temporary Azure access token
      ↓
Workflow accesses Foundry
```

Three concepts should stay separate:

### Service principal

The Azure identity representing the GitHub workflow.

Example:

```text
foundry-prompt-agent-github
```

### Federated credential

The trust relationship that says which GitHub workload is allowed to become that Azure identity.

It validates values such as:

```text
Issuer
Subject
Audience
```

### Azure RBAC

Determines what the authenticated service principal may do after login.

Mental model:

```text
Service principal
= Who GitHub is in Azure

Federated credential
= Which GitHub workload may become that identity

RBAC
= What that identity is allowed to do
```

---

## 6. GitHub Repository Variables

The workflow reads environment-specific configuration from GitHub repository variables:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID

FOUNDRY_PROJECT_ENDPOINT
FOUNDRY_AGENT_NAME
FOUNDRY_AGENT_VERSION
FOUNDRY_JUDGE_MODEL

BEHAVIOR_PASS_RATE_THRESHOLD
SCOPE_PASS_RATE_THRESHOLD
```

No Azure client secret is required when OIDC federation is used.

---

## 7. The Regression Dataset

The source-of-truth regression specification lives in Git:

```text
evals/contoso_agent_eval_v3.jsonl
```

It captures known product requirements such as:

- exact menu retrieval
- price accuracy
- filtering
- budget arithmetic
- semantic recommendations
- abstention when data is unavailable
- hallucination resistance
- ambiguity handling
- scope adherence

Important distinction:

```text
contoso_agent_eval_v3.jsonl
        ↓
Golden regression specification
        ↓
Version-controlled in Git

results_v3.jsonl
        ↓
Fresh responses from one execution
        ↓
Evaluation evidence
```

Earlier dataset versions remain in `evals/` as a record of how the benchmark grew.

Git versions the benchmark.

Foundry stores evaluation execution evidence.

---

## 8. Unique Dataset and Evaluation Run Versions

Generated response datasets should not reuse a fixed Foundry dataset version because Foundry dataset versions are immutable.

Instead, CI should derive a unique identifier from the Git commit SHA.

Example:

```text
Git commit:      a31c42f9
Dataset version: a31c42f9
Evaluation run:  contoso-regression-a31c42f9
```

Conceptually:

```python
github_sha = os.getenv("GITHUB_SHA")

RUN_ID = (
    github_sha[:8]
    if github_sha
    else datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
)
```

This provides traceability between source changes, generated outputs, evaluation runs, and GitHub workflow executions.

---

## 9. Quality Gates

Running an evaluation in CI is useful, but it is not yet a gate.

A real gate means:

> If quality is below the required level, return a non-zero process exit code so GitHub marks the workflow as failed.

For this project:

```text
Behavior rubric pass rate >= 90%
Scope adherence pass rate == 100%
Evaluation run status == completed
```

Example policy:

```text
contoso_behavior_rubric >= 0.90
contoso_scope_adherence >= 1.00
```

The same run also measures token cost and appends the modeled business economics to `evals/tokenomics_history.jsonl`. Those economics are deliberately **not** gated: they rest on business assumptions, and a build should fail on measured quality regressions only.

Conceptually:

```python
if behavior_pass_rate < behavior_threshold:
    failures.append("Behavior regression")

if scope_pass_rate < scope_threshold:
    failures.append("Scope regression")

if failures:
    raise SystemExit(1)
```

GitHub interprets:

```text
exit 0 → workflow passes
exit 1 → workflow fails
```

That is the bridge from **evaluation metric** to **release policy**.

---

## 10. Why Pass Rate Instead of a Generic Score

For product-specific regression gating, evaluator **pass rate** is easier to reason about than a generic average LLM score.

Example:

```text
Behavior rubric
28 / 30 cases pass
= 93.3% pass rate
```

This directly answers:

> How many required behaviors still work?

For especially important invariants, stricter gates are appropriate.

Example:

```text
Scope adherence = 100%
```

---

## 11. Pull Request Protection

Once the workflow is stable, configure GitHub branch protection or a ruleset so the regression workflow becomes a required check for `main`.

```text
Pull request
     ↓
Regression evaluation
     ↓
Quality gate

PASS
 ↓
Merge allowed

FAIL
 ↓
Merge blocked
```

This turns agent evaluation from an informational dashboard into enforceable engineering policy.

---

## 12. Failure Investigation

A failed CI run should provide enough information to diagnose the problem.

Useful output:

```text
Behavior rubric: 83.3%
Required: >= 90%

Scope adherence: 100%
Required: 100%

QUALITY GATE FAILED
```

The harness should also print the Foundry report URL when available.

Debugging loop:

```text
GitHub detects regression
        ↓
Engineer opens Foundry evaluation report
        ↓
Inspect failed rows
        ↓
Inspect evaluator reasoning
        ↓
Inspect traces if needed
        ↓
Determine root cause
        ↓
Fix prompt/tool/model/data
```

Useful mental model:

> **CI detects. Foundry diagnoses.**

---

## 13. Scheduled vs CI vs Continuous Evaluation

These mechanisms solve different problems.

| Mechanism | Main question |
|---|---|
| CI regression | Did this proposed change break known behavior? |
| Scheduled evaluation | Did known behavior drift over time? |
| Continuous evaluation | What is happening on real production traffic? |

Together:

```text
KNOWN BEHAVIOR

GitHub PR
   ↓
CI regression suite
   ↓
Protect changes before merge


DEPLOYED BEHAVIOR

Weekly schedule
   ↓
Same benchmark
   ↓
Detect drift


REAL USERS

Production traffic
   ↓
Sampled continuous evaluation
   ↓
Discover new failure patterns
```

---

## 14. The Enterprise Feedback Loop

The most important pattern is not the YAML itself.

It is the lifecycle:

```text
Requirements
     ↓
Curated evaluation dataset
     ↓
CI regression gate
     ↓
Release
     ↓
Production monitoring
     ↓
Continuous evaluation
     ↓
Interesting failure / edge case
     ↓
Add permanent regression case
     ↓
Dataset becomes stronger
     ↓
Future CI runs catch that failure
```

A production failure should ideally become a permanent regression case.

---

## 15. Responsibility Boundaries

### Foundry owns

- persisted Prompt Agent runtime
- model and tool execution
- evaluation execution infrastructure
- custom evaluator hosting
- judge-model calls
- aggregate and row-level evaluation results
- evaluation persistence
- monitoring surfaces
- portal visualization

### Our project owns

- regression dataset design
- Python evaluation harness
- evaluator selection
- quality thresholds
- agent/version selection
- CI orchestration
- release policy
- failure-handling logic

### GitHub owns

- event triggering
- temporary CI runner
- repository checkout
- OIDC token issuance
- workflow execution
- check status on pull requests

---

## 16. What Would Change With LangGraph?

Very little about the evaluation lifecycle.

The target changes from:

```text
Foundry Prompt Agent
```

to:

```text
LangGraph application
```

But the surrounding ADLC remains:

```text
dataset
  ↓
execute agent
  ↓
evaluate
  ↓
threshold
  ↓
CI gate
  ↓
production traces
  ↓
new regression cases
```

Key lesson:

> **Evaluation and regression engineering sit above the agent framework.**

---

## 17. Minimal Enterprise-Ready Checklist

- [x] A curated regression dataset is version-controlled in Git.
- [x] The persisted Foundry agent can be invoked from Python.
- [x] Evaluation runs execute programmatically.
- [x] Product-specific custom evaluators are used.
- [x] GitHub authenticates to Azure using OIDC rather than a stored client secret.
- [x] CI dependencies are reproducible through `uv.lock`.
- [x] Dataset/evaluation execution IDs are unique and traceable to commits.
- [x] Quality thresholds are explicit.
- [x] Evaluation failures produce a non-zero CI exit code.
- [x] Pull requests can run the regression workflow.
- [x] The workflow can be configured as a required branch check.
- [x] Scheduled Foundry evaluation periodically rechecks the deployed agent.
- [x] Foundry evaluation reports remain available for diagnosis.

---

# Architecture Journal

## What did Foundry automate?

Foundry provides the managed Prompt Agent runtime, scalable evaluator execution, custom evaluator hosting, judge-model calls, evaluation persistence, aggregate metrics, row-level results, monitoring, and portal-based investigation.

## What control did we retain?

We control the regression dataset, evaluator choice, quality thresholds, agent/version selection, CI behavior, release policy, and failure handling.

## What would we need to build without Foundry?

Without a managed evaluation platform, the team would need to build or integrate evaluator execution infrastructure, judge-model invocation, run persistence, evaluation versioning, metrics aggregation, result visualization, trace correlation, monitoring, and quality trend tracking.

---

# Key Takeaway

Traditional software CI asks:

> Did the tests pass?

Agent CI asks:

> Is this version still good enough across the important behaviors we have defined?

The resulting pattern is:

```text
Agent change
   ↓
Regression dataset
   ↓
Evaluators
   ↓
Quality thresholds
   ↓
CI gate
   ↓
Production monitoring
   ↓
New regression cases
```

That closes the **Build → Evaluate → Optimize → Monitor → Automate** loop for the Prompt Agent lifecycle.
