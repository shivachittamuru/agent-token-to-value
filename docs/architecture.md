---
title: Agent Token-to-Value Architecture
description: The evidence, cost, economics, decision, and presentation boundaries in the project.
---

## System flow

```text
Agent execution → evaluation → Accepted Work → execution evidence
       → business assumptions / outcomes → economic value
       → decision gates → portfolio action
```

Accepted Work is produced only after task success and mandatory quality
guardrails pass. Business outcomes and incrementality need downstream evidence;
they are not inferred from an accepted response.

## Cost architecture

```text
Azure Cost Management ─┐
                       ├→ normalized cost evidence → allocation
FOCUS Cost and Usage ──┘                              → cost snapshot
                                                         → system economics
```

The source adapters preserve provenance and normalize resource-level evidence.
The allocator applies the configured allow-list and allocation rules. Snapshots
are period-level evidence, not per-run cost.

## Evidence boundaries

* **Measured:** directly recorded technical or operational evidence.
* **Modeled:** calculated using explicit assumptions and measured inputs.
* **Simulated:** generated outcomes scoped to a seeded simulation, not production.
* **Unknown:** required evidence is absent; it is not zero or false.

## Economic boundaries

```text
Model → System → Customer
```

Model economics compare modeled contribution with projected inference cost.
System economics compare it with allocated Azure runtime cost. Customer
economics require attributable incremental outcomes and Total Relevant Customer
Cost, which remain unestablished.

## Design principles

* Unknown is not zero.
* Accepted Work bridges AI output and value.
* Cost sources normalize before economics.
* Allocation is centralized.
* Period-level Azure cost is not run-level cost.
* Modeled economics are not realized ROI.
* Decision gates constrain actions; they are not a composite score.

## Code boundaries

| Responsibility | Modules |
|---|---|
| Cost ingestion | `azure_cost_management.py`, `focus_cost.py` |
| Cost normalization and allocation | `azure_runtime_cost.py` |
| Cost persistence | `cost_snapshot.py`, `run_artifacts.py` |
| Execution and evaluation | `execution.py`, `foundry_eval.py` |
| Economics | `business_economics.py`, `economic_value.py`, `incremental_economics.py`, `value_resilience.py` |
| Assessment and decision | `workload_assessment.py`, `decision_gates.py`, `portfolio_action.py` |
| Presentation | `dashboard_views.py`, `apps/dashboard.py`, `apps/value_to_action_dashboard.py` |

Keep these boundaries as-is. Future candidates, only if growth warrants it,
are splitting presentation formatting from Streamlit apps, separating the
history-based and run-package-based dashboard data loaders, and extracting
shared cost-evidence validation. No broad modularization is needed now.
