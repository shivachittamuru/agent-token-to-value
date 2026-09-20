# Business Outcome Evidence Record — v1

## Decision Question

What evidence must be captured after Accepted Work to determine whether the AI interaction changed the customer journey or produced a business outcome?

## Core Rule

Accepted Work and Business Outcome evidence must remain separate.

```text
Accepted Work
      ↓
Workflow Outcome
      ↓
Business Outcome
      ↓
Incrementality
```

Evidence from one layer must not be silently promoted into the next.

## Minimum Evidence Record

Each interaction should be capable of carrying:

| Field | Meaning |
|---|---|
| `run_id` | Technical/evaluation run identity |
| `workload_id` | Stable workload identity |
| `interaction_id` | Stable interaction identity used to join evidence |
| `accepted` | Whether the interaction became Accepted Work |
| `customer_engaged_after_response` | Whether downstream customer engagement was observed |
| `order_completed` | Whether an order completion was observed |
| `order_id` | Opaque downstream order identifier when available |
| `order_value_usd` | Observed order amount when available |
| `incremental_order` | Whether evidence supports that the order would not otherwise have occurred |
| `counterfactual_method` | Method used to establish incrementality |
| `outcome_evidence_source` | System or dataset providing the downstream evidence |
| `outcome_observed_at_utc` | Time the downstream outcome was observed |

## Evidence States

`True`, `False`, and `Unknown` have different meanings.

```text
True
=
the event was observed

False
=
the event was observed not to occur

None / Unknown
=
we do not have sufficient evidence
```

Do not convert missing downstream evidence into `False`.

## Current Regression Environment

The current Contoso evaluation run measures:

```text
Interaction
      ↓
Execution Evidence
      ↓
Accepted Work
```

It does not represent real customer commerce activity.

Therefore the current Business Outcome Evidence Record should legitimately contain:

```text
customer_engaged_after_response = None
order_completed = None
order_id = None
order_value_usd = None
incremental_order = None
counterfactual_method = None
```

This means:

> Business outcome evidence has not yet been collected.

It does not mean:

> No business outcome occurred.

## Observed Outcome vs Incremental Outcome

Even when an order is observed:

```text
order_completed = True
```

incrementality can still remain:

```text
incremental_order = None
```

because:

```text
Observed Order
      ≠
Incremental Order
```

The customer may have purchased without the AI interaction.

## Counterfactual Evidence

`incremental_order` should only become known when supported by a defensible comparison such as:

- control or holdout group,
- randomized experiment,
- phased rollout,
- matched historical baseline,
- comparable staff-unavailable periods,
- another explicit counterfactual design.

The method should be recorded in `counterfactual_method`.

## Provenance

Business outcome evidence should preserve where it came from.

Examples include:

- ordering system,
- POS transaction system,
- CRM,
- customer-session telemetry,
- experiment platform.

Use opaque identifiers when linking systems; avoid placing unnecessary customer-identifying information in the economic record.

## Evidence Join

The intended evidence chain is:

```text
Execution Record
      │
      │ interaction_id
      ▼
Accepted Work
      │
      │ interaction_id
      ▼
Business Outcome Evidence
      │
      ▼
Observed Workflow / Order Outcome
```

The join must use stable identity rather than positional ordering.

## Current Evidence Boundary

Today:

```text
Accepted Work
=
Measured
```

while:

```text
Customer engagement
Order completion
Order value
Incrementality
=
Unknown
```

This boundary should remain explicit until a real-world pilot supplies downstream evidence.

## Key Takeaways

- Accepted Work does not imply a downstream business outcome.
- Missing outcome evidence is Unknown, not a negative outcome.
- Observing an order does not prove that the AI caused the order.
- Incrementality requires explicit counterfactual evidence.
- Technical and business evidence may originate in different systems and at different times.
- Stable interaction identity is what allows those evidence layers to be joined.
- Provenance should travel with business outcome evidence.
- Regression testing can prove technical behavior but cannot prove realized customer value.

## Next Step

Implement the Business Outcome Evidence Record and demonstrate that the current regression run preserves downstream outcomes as Unknown rather than fabricating business evidence.