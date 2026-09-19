# Foundry Prompt Agent — From Agent Quality to Token Economics

A small learning project that walks through the **Microsoft Foundry Prompt Agent lifecycle (ADLC)** using a simple *Contoso Coffee* assistant backed by **Azure AI Search** — and then extends that lifecycle into **token economics**.

The project starts with a familiar agent question:

> **Does the agent work reliably?**

and deliberately pushes one step further:

> **Is the AI economically worth operating?**

The tokenomics story is built around a realistic local-business scenario: a coffee shop may receive more menu-related calls and inquiries than staff can answer during peak periods. The baseline is not necessarily “replace a human worker.” It may be:

```text
Phone rings
   ↓
Staff is busy
   ↓
Nobody answers
   ↓
Customer gives up
   ↓
Revenue disappears
```

The project therefore treats the agent as a **demand-recovery system** and asks:

> **How much otherwise-lost contribution can AI potentially recover per dollar of inference?**

The core optimization goal is:

> **Maximize economically valuable outcomes per dollar of AI inference while preserving quality — not simply minimize token consumption.**

---

## Project versions

The original Token-to-Value implementation is preserved as the Git tag:

`token-to-value-v1`

Value-to-Action development continues on:

`feature/value-to-action`

---

## Overview

The Contoso Coffee agent answers questions about a coffee-shop menu: prices, descriptions, filtering, budget math, recommendations, abstention when information is unavailable, and scope adherence.

The important architectural split is:

- **The Prompt Agent itself lives in Microsoft Foundry.** Its instructions, model, and Azure AI Search tool are configured and persisted there.
- **This repository owns everything around the agent:** invocation, evaluation, regression datasets, token measurement, business-economics modeling, CI quality gates, reports, and an interactive tokenomics dashboard.

The project demonstrates two related ideas:

1. **Agent trust comes from repeatable evaluation evidence**, not a few successful playground conversations.
2. **Token cost only becomes meaningful when connected to quality and business outcomes.**

---

## Architecture / mental model

```text
                     AGENT QUALITY

User / Evaluation Dataset
         ↓
  Foundry Prompt Agent
         ↓
      GPT model
         ↓
    Azure AI Search
         ↓
       Response
         ↓
Python evaluation harness
         ↓
   Foundry evaluators
         ↓
Measured quality + token usage
         ↓
CI quality gate


                    TOKEN ECONOMICS

Measured quality + token cost
         +
Business assumptions
         ↓
business_economics.py
         ↓
Recovered demand
         ↓
Recovered contribution
         ↓
AI Value Multiple
         ↓
Report / Streamlit dashboard
```

The Python side invokes the persisted agent and drives evaluation. Foundry owns the managed agent runtime, model/tool execution, evaluator catalog, and evaluation-result persistence.

The repository then adds the application-specific economics layer.

---

## Project structure

Only the parts that matter for understanding the flow:

| Path | Purpose |
| --- | --- |
| [src/foundry_prompt_agent/](src/foundry_prompt_agent/) | Reusable Python package around the persisted Foundry agent. |
| [src/foundry_prompt_agent/agent.py](src/foundry_prompt_agent/agent.py) | Invokes the existing Prompt Agent and captures token usage returned by the Responses API. |
| [src/foundry_prompt_agent/tokenomics.py](src/foundry_prompt_agent/tokenomics.py) | Generic token-cost, efficiency, and effectiveness calculations. |
| [src/foundry_prompt_agent/business_economics.py](src/foundry_prompt_agent/business_economics.py) | Coffee-shop demand-recovery economics: recovered orders, contribution, AI Value Multiple, and break-even conversion. |
| [src/foundry_prompt_agent/foundry_eval.py](src/foundry_prompt_agent/foundry_eval.py) | Foundry evaluation mechanics: dataset upload, evaluation run, polling, pass rates, and the quality gate. |
| [src/foundry_prompt_agent/history.py](src/foundry_prompt_agent/history.py) | Reads and appends the tokenomics experiment ledger, ignoring rows from older schemas. |
| [scripts/run_evaluation.py](scripts/run_evaluation.py) | Main evaluation entrypoint: runs the agent, measures token usage, runs Foundry evaluators, enforces quality gates, and persists run history. |
| [scripts/generate_economics_report.py](scripts/generate_economics_report.py) | Generates a Markdown economics report from the latest measured run without calling the model again. |
| [scripts/plot_tokenomics.py](scripts/plot_tokenomics.py) | Plots tokenomics trends across historical evaluation runs. |
| [apps/dashboard.py](apps/dashboard.py) | Interactive Streamlit dashboard for scenario analysis and run/agent comparison. |
| [economics/business_assumptions.yaml](economics/business_assumptions.yaml) | Explicit business assumptions used by the economics model. |
| [evals/](evals/) | Curated regression datasets, generated responses, and tokenomics run history. |
| [evals/tokenomics_history.jsonl](evals/tokenomics_history.jsonl) | Append-only experiment ledger containing measured AI metrics, assumptions, and modeled economics. |
| [tests/](tests/) | Unit tests for the pure tokenomics, economics, and history logic. |
| [data/contoso.json](data/contoso.json) | Contoso Coffee menu that backs the Azure AI Search index. |
| [docs/](docs/) | Setup, evaluation, monitoring, automation, tokenomics framework, and business-case documentation. |
| [.github/workflows/](.github/workflows/) | CI regression workflows. |

All commands in this README are run from the repository root.

---

## Prerequisites

- **Python `>=3.12`** (see [pyproject.toml](pyproject.toml)).
- **[uv](https://docs.astral.sh/uv/)** for dependency management and running scripts.
- **Azure CLI** (`az`) — the local client authenticates with `AzureCliCredential`.
- Access to the appropriate **Microsoft Foundry project**.
- An existing **Prompt Agent** and **Azure AI Search** configuration in that Foundry project.
- The custom evaluators `contoso_behavior_rubric` and `contoso_scope_adherence` registered in Foundry.

If starting from scratch, follow [docs/create_prompt_agent.md](docs/create_prompt_agent.md) first.

---

## Setup with uv

```bash
# clone and enter the repo
git clone <your-fork-or-repo-url>
cd foundry-prompt-agent

# install the locked environment
uv sync

# sign in so AzureCliCredential can get a token
az login

# create your local env file and fill in the values
cp .env.example .env
```

Verify the pure tokenomics, economics, and history logic at any time:

```bash
uv run pytest -q
```

Populate `.env` with your Foundry project details:

```text
FOUNDRY_PROJECT_ENDPOINT=
FOUNDRY_AGENT_NAME=foundry-prompt-agent
FOUNDRY_AGENT_VERSION=
FOUNDRY_JUDGE_MODEL=gpt-5

BEHAVIOR_PASS_RATE_THRESHOLD=0.90
SCOPE_PASS_RATE_THRESHOLD=1.00
```

Business assumptions are intentionally kept separate from runtime configuration in:

```text
economics/business_assumptions.yaml
```

Example:

```yaml
business:
  missed_contacts_per_day: 100
  ai_eligible_rate: 0.60
  conversion_rate: 0.30
  average_order_value_usd: 10.00
  contribution_margin: 0.35
  days_per_month: 30
```

These are **scenario assumptions**, not claims about a real coffee shop.

---

## Running the agent

Invoke the persisted Foundry Prompt Agent directly:

```bash
uv run src/foundry_prompt_agent/agent.py
```

This confirms the Foundry endpoint, agent reference, Azure authentication, and response path work end to end.

---

## Running evaluations

```bash
uv run scripts/run_evaluation.py
```

[scripts/run_evaluation.py](scripts/run_evaluation.py) performs the core measurement loop:

1. Loads the curated regression dataset from `evals/`.
2. Invokes the persisted agent for every case.
3. Captures actual token usage and computes token cost.
4. Uploads generated responses to Foundry.
5. Runs the custom Foundry evaluators:
   - `contoso_behavior_rubric`
   - `contoso_scope_adherence`
6. Calculates:
   - tokens per interaction,
   - cost per interaction,
   - behavior success rate,
   - tokens per successful resolution,
   - cost per successful resolution.
7. Combines measured AI performance with the configured business assumptions.
8. Calculates modeled demand recovery and token economics.
9. Appends the run to `evals/tokenomics_history.jsonl`.
10. Enforces the CI quality thresholds and exits non-zero on regression.

Only step 10 can fail the build. Behavior and scope pass rates are the gates; the
business economics are recorded for analysis, never enforced.

A Foundry report URL is printed for diagnosis.

See [docs/evaluation.md](docs/evaluation.md) for the evaluation design and evaluator rationale.

---

## Token-to-value ladder

The project deliberately moves from raw model usage to economic accountability:

```text
Token Spend
    ↓
How many tokens did we use?

Token Cost
    ↓
What did those tokens cost?

Token Efficiency
    ↓
What did one interaction cost?

Token Effectiveness
    ↓
What did one successful resolution cost?

Business Economics
    ↓
What might a successful interaction be worth?

Economic Value
    ↓
How much recovered contribution
do we create per dollar of AI inference?
```

The generic framework is documented in:

**[docs/token_to_value_ladder.md](docs/token_to_value_ladder.md)**

That document explains the reusable measurement ladder, why quality must be part of token economics, how the ladder maps to this repository, and why a cheaper agent is not automatically an economically better agent.

---

## Business case and economics

The Contoso Coffee application of the framework is documented separately in:

**[docs/business_case_and_economics.md](docs/business_case_and_economics.md)**

That document explains the business story:

```text
Missed customer demand
        ↓
AI-addressable interactions
        ↓
Measured agent quality
        ↓
Successfully served customers
        ↓
Expected conversion
        ↓
Recovered revenue
        ↓
Recovered contribution
```

The primary business metric is:

```text
AI Value Multiple
=
Recovered Contribution
÷
AI Inference Cost
```

The purpose is not to claim a precise production ROI from a pet-project dataset.

Instead, the project keeps three categories strictly separate:

```text
Measured   token usage, inference cost, behavior success rate,
           cost per successful resolution

Assumed    missed contacts/day, AI-eligible rate, conversion rate,
           average order value, contribution margin

Unproven   actual recovered demand, incremental orders, and conversion
           lift, which only a real pilot can establish
```

This keeps the economics transparent and testable.

---

## Generate the economics report

Once at least one evaluation run has been recorded:

```bash
uv run scripts/generate_economics_report.py
```

This does **not** rerun the agent.

It reads the latest measured run from:

```text
evals/tokenomics_history.jsonl
```

and combines that measurement with business scenarios locally.

The generated report summarizes:

- measured AI performance,
- business assumptions,
- demand-recovery funnel,
- recovered revenue and contribution,
- AI inference cost,
- AI Value Multiple,
- break-even conversion,
- conversion sensitivity.

The important separation is:

```text
scripts/run_evaluation.py
=
measure the AI

scripts/generate_economics_report.py
=
analyze the economics of that measurement
```

Business sensitivity analysis therefore costs no additional inference tokens.

---

## Interactive tokenomics dashboard

For interactive scenario exploration:

```bash
uv run streamlit run apps/dashboard.py
```

The Streamlit dashboard reads the same measured history and performs all scenario modeling locally.

### Business Economics tab

Measured AI metrics stay fixed — behavior success rate, tokens per interaction, measured cost per interaction, and cost per successful resolution. The sidebar changes only assumptions: missed contacts/day, AI-eligible rate, conversion rate, average order value, contribution margin, and an AI cost stress multiplier.

The funnel, recovered revenue and contribution, monthly AI inference cost, AI Value Multiple, and break-even conversion recalculate on every change. **Conservative / Base / Optimistic** presets jump between coherent scenarios.

The cost-stress control deliberately preserves the measured inference cost and models scenarios such as `5x`, `10x`, or `20x` production cost rather than overwriting the measurement.

### Agent / Run Comparison tab

Two historical evaluation runs are compared under the **same business assumptions**, so quality and inference cost are the only variables: tokens per interaction, measured cost per interaction, behavior quality, cost per successful resolution, AI Value Multiple, and break-even conversion.

This demonstrates a core tokenomics lesson:

> **The lowest-token or cheapest agent is not necessarily the economically best agent.**

A more expensive configuration can be preferable if higher quality creates more valuable successful outcomes.

---

## Run history and visualization

Every current evaluation run appends measured and modeled values to:

```text
evals/tokenomics_history.jsonl
```

Treat this file as an **experiment ledger**.

Each run can preserve:

```text
Measured AI performance
+
Business assumptions
+
Modeled economics
```

This enables later comparisons to answer:

> Did economics change because the agent changed, or because the business assumptions changed?

Run-history visualizations can be regenerated with:

```bash
uv run scripts/plot_tokenomics.py
```

The most useful trend metrics are:

- success rate,
- tokens per interaction,
- cost per interaction,
- cost per successful resolution,
- AI Value Multiple.

---

## CI/CD regression gate

Workflows under [.github/workflows/](.github/workflows/) automate regression evaluation.

The primary workflow runs the repository's own `scripts/run_evaluation.py`, giving the project control over:

- dependency versions,
- regression dataset,
- agent version,
- evaluator selection,
- quality thresholds,
- failure behavior.

The workflow:

```text
Pull request / manual run
        ↓
GitHub Actions
        ↓
OIDC authentication to Azure
        ↓
uv sync --locked
        ↓
scripts/run_evaluation.py
        ↓
Foundry evaluation
        ↓
behavior + scope thresholds
        ↓
PASS / FAIL
```

GitHub authenticates through **OIDC workload identity federation**, so no long-lived Azure client secret is required.

For the full CI reasoning, federated identity setup, scheduled evaluation, and quality-gate design, see:

**[docs/automation.md](docs/automation.md)**

---

## Learning journey / ADLC

The repository walks through the Agent Development Lifecycle:

```text
Build
  ↓
Prompt Agent configured in Foundry

Observe
  ↓
Traces and agent behavior

Evaluate
  ↓
Curated datasets + custom evaluators

Optimize
  ↓
Agent Optimizer

Monitor
  ↓
Continuous / scheduled evaluation

Automate
  ↓
GitHub Actions regression gates

Measure Economics
  ↓
Tokens → quality → business value
```

The recurring theme is:

> **Trust comes from repeatable evaluation evidence, and value comes from measuring spend against outcomes rather than counting tokens in isolation.**

---

## Documentation

Conceptual notes under [docs/](docs/):

- [docs/create_prompt_agent.md](docs/create_prompt_agent.md) — create the Azure AI Search index, Prompt Agent, instructions, and search tool.
- [docs/evaluation.md](docs/evaluation.md) — curated datasets, evaluator design, cloud evaluation, baselines, custom evaluators, and Agent Optimizer.
- [docs/monitoring.md](docs/monitoring.md) — operational vs. AI-quality health, traces, continuous/scheduled evaluation, and monitoring.
- [docs/automation.md](docs/automation.md) — scheduled regression, GitHub Actions, OIDC federation, and CI quality gates.
- **[docs/token_to_value_ladder.md](docs/token_to_value_ladder.md)** — the reusable tokenomics framework from token spend to economic value.
- **[docs/business_case_and_economics.md](docs/business_case_and_economics.md)** — the Contoso Coffee demand-recovery business case, assumptions, AI Value Multiple, break-even analysis, sensitivity, and demo story.

A useful reading order is:

```text
create_prompt_agent.md
        ↓
evaluation.md
        ↓
monitoring.md
        ↓
automation.md
        ↓
token_to_value_ladder.md
        ↓
business_case_and_economics.md
```

---

## Key takeaway

A traditional agent demo often stops at:

```text
Agent answered correctly.
```

This project pushes further:

```text
Did it answer correctly?
        ↓
What did that interaction cost?
        ↓
What did a successful interaction cost?
        ↓
What business outcome might it support?
        ↓
How much recovered contribution
do we get per dollar of inference?
```

That is the project's main value proposition:

> **Move from agent capability to agent accountability — technically through evaluation, and economically through token-to-value measurement.**

---

## Future work

Keep future extensions small and evidence-driven:

- Grow the regression dataset from real traces and failure cases.
- Compare prompt/model/agent configurations using quality + economic metrics rather than token cost alone.
- Add real business measurements if the scenario is ever piloted with an actual operator.
- Extend the current inference-cost model into fully loaded economics only when review, operational, and failure/risk costs can be grounded in evidence.
