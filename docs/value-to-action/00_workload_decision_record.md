# Value-to-Action Workload Record — v1

## Workload
**ID:** `contoso-demand-recovery`

AI-assisted resolution of otherwise-unanswered, AI-eligible customer menu inquiries during periods when staff cannot respond.

## Business Problem
During staff-constrained periods, some customer inquiries may go unanswered, creating the possibility of abandoned demand.

## Baseline / Counterfactual
Without the AI capability, some eligible inquiries may remain unanswered and some associated demand may be lost.

> The current assumption of `100 missed contacts/day` is a scenario input, not an evidenced baseline.

## Business Hypothesis
Successful AI resolution may preserve customer intent, leading to otherwise-lost orders and recovered contribution.

## Current Decision
Does the available evidence justify moving this workload from a modeled business case into a bounded real-world pilot, and what evidence must that pilot produce before broader investment is justified?

## Current Implementation
Foundry Prompt Agent  
→ GPT model  
→ Azure AI Search  
→ response  
→ evaluation / quality gates  
→ token and economics analysis

## Current Economic Metric
**Modeled AI Value Multiple**

Modeled recovered contribution  
÷  
Measured model inference cost

This is useful for scenario analysis, but it is not yet full customer ROI because total system cost and realized business outcomes are not yet known.

## Evidence State

### Measured
- Model/token usage
- Model inference cost
- Behavior evaluation
- Scope-adherence evaluation
- Tokens per interaction
- Inference cost per interaction
- Quality-adjusted cost per successful interaction

### Assumed
- Missed contacts/day
- AI-eligible rate
- Conversion rate
- Average order value
- Contribution margin
- Operating days/month

### Unknown / Unproven
- Actual missed-demand baseline
- Actual incremental orders
- Realized recovered contribution
- Full system execution cost
- Human review / escalation cost
- Failure / recovery cost
- Persistence over time
- Incremental expansion economics
- Operational dependency

## Current Takeaway
The project has real technical and quality evidence, but the business-value case is still partly modeled.

The next step is to define exactly what counts as an **Accepted Work Unit** before extending the cost and value model.