---
title: Agent Token-to-Value
description: A practical framework for measuring AI work, economic value, and investment decisions.
---

## Agent Token-to-Value

A practical framework for measuring whether AI workloads convert resource
consumption into verified work, business outcomes, economic value, and
investment decisions.

```text
Consumption → AI Work → Useful Progress → Verification → Accepted Outcome
     → Business Outcome → Economic Value → Decision / Action
```

## Why this exists

* Token cost alone does not show whether AI is economically useful.
* A successful model response is not the same as verified business value.
* Investment decisions need evidence, cost boundaries, and explicit action rules.

## Economic boundaries

| Layer | Question | Example metric |
|---|---|---|
| Model economics | Is inference efficient? | Modeled AI Value Multiple |
| System economics | Is the broader AI system economical? | Modeled Azure Runtime Value Multiple |
| Customer economics | Does incremental value exceed total relevant customer cost? | Customer Net Economic Value |

Model economics use projected inference cost only. System economics use
allocated Azure runtime cost. Customer economics require attributable outcomes
and Total Relevant Customer Cost, which are not yet established.

## Cost-source adapters

```text
Azure Cost Management API ─┐
                           ├→ normalized evidence → allocation → economics
FOCUS Cost and Usage ──────┘
```

The Azure adapter reads Azure-native billing. The FOCUS adapter reads a
standardized cost-and-usage CSV shape. Both feed the same allocation and
economics path. This proves the adapter pattern, not full multi-cloud support.

## Dashboards

* **AI Value Pulse** is the recommended starting dashboard. It presents the
  workflow from work through evidence, value, and next action in one compact view.
* **Token-to-Value** measures technical performance and Accepted Work, then
  models business economics. A compatible cost snapshot makes system
  economics primary; the inference-only metric remains diagnostic.
* **Value-to-Action** presents evidence sufficiency and modeled, system, and
  customer economics to inform actions such as PROVE, OPTIMIZE, SCALE, PAUSE,
  or RETIRE.

## Quick start

Install dependencies and configure the Foundry connection:

```powershell
uv sync
az login
Copy-Item .env.example .env
```

Set `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_AGENT_NAME`, and related evaluation
settings in `.env`. An existing Foundry Prompt Agent, Search connection, and
custom evaluators are required. See the [agent setup guide](docs/create_prompt_agent.md).

Run regression evaluation:

```powershell
uv run python scripts\run_evaluation.py
```

Run with a local Azure runtime cost snapshot:

```powershell
uv run python scripts\run_evaluation.py --cost-snapshot cost_snapshots\contoso-demand-recovery-2026-09.json
```

Open the recommended starting dashboard or a detailed view:

```powershell
uv run streamlit run apps\value_pulse_dashboard.py
uv run streamlit run apps\dashboard.py
uv run streamlit run apps\value_to_action_dashboard.py
```

Validate the local FOCUS sample without Azure access:

```powershell
uv run python scripts\read_focus_runtime_cost.py --input focus_samples\contoso-september-2026.csv --month 2026-09 --cost-metric effective_cost
```

Run tests with `uv run pytest -q`.

## Documentation

* [Architecture](docs/architecture.md) is the current system overview.
* [Token-to-Value ladder](docs/token_to_value_ladder.md) defines the measurement progression.
* [Business economics](docs/business_case_and_economics.md) records the Contoso model and its evidence status.
* [Azure runtime cost](docs/azure_runtime_cost.md) covers billing adapters, allocation, and snapshots.
* [Value-to-Action](docs/value-to-action/README.md) describes evidence-based decisions.
* [Project versions](docs/project_versions.md) summarizes major milestones.

Implementation and setup references remain in [docs/](docs/), including
[evaluation](docs/evaluation.md), [monitoring](docs/monitoring.md),
[automation](docs/automation.md), and [custom evaluator](docs/custom_evaluators.md)
guides.
