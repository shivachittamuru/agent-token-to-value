# Project Versions and Development Branches

The repository grows in layers: **Agent Quality → Token-to-Value → Value-to-Action**. Each checkpoint preserves the previous one rather than replacing it.

## `token-to-value-v1`

The original Token-to-Value implementation:

- Foundry Prompt Agent evaluation flow
- token-cost and token-effectiveness economics
- business-economics model
- original Streamlit tokenomics dashboard ([apps/dashboard.py](../apps/dashboard.py))
- reports, tests, and CI evaluation workflow

```bash
git checkout token-to-value-v1
```

## `value-to-action-v1`

The tag intended after `feature/value-to-action` is merged to main. It extends — does not redefine — Token-to-Value with:

- Accepted Work (task success + mandatory guardrails)
- run-centric evidence package (`runs/<run_id>/`)
- the Value-to-Action methodology (MEASURE → PROVE → VALUE → TEST → DECIDE → ACT)
- simulation mode with explicit synthetic provenance
- synthetic experiment and synthetic population economics
- the Value-to-Action dashboard ([apps/value_to_action_dashboard.py](../apps/value_to_action_dashboard.py))

## Next branch

The next intended development branch is **`feature/finops-cost-integration`**. It will extend technical/runtime **cost coverage** (broader Azure runtime cost evidence) rather than redefine the Value-to-Action methodology. It is not yet implemented.