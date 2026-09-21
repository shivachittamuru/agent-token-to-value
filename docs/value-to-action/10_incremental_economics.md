# Incremental Economics — v1

## Decision Question

If we make an additional investment in this workload, what additional value and additional cost would that investment create?

## Core Rule

Investment decisions should be based on the economics of the proposed change, not only on the economics of the workload that already exists.

```text
Additional Economic Value
        -
Additional Cost Required
        =
Incremental Net Economic Value
```

Or:

```text
ΔNEV = ΔValue - ΔCost
```

## Current Economics vs Incremental Economics

These answer different questions.

### Current / Average Economics

```text
Value already produced
──────────────────────
Cost already incurred
```

Useful for:

> Is the workload economically healthy today?

### Incremental Economics

```text
Additional Value from Proposed Change
-
Additional Cost Caused by Proposed Change
```

Useful for:

> Has this workload earned the right to consume more resources?

A strong historical value multiple does not automatically justify further investment.

## Define the Increment

Incremental economics is meaningless unless the proposed change is explicit.

Examples:

- serve an additional 1,000 eligible inquiries per month,
- expand from one store to ten stores,
- extend operating hours,
- add another customer workflow,
- improve the quality target,
- add mandatory human review,
- move to a higher-capacity Search tier,
- deploy into another geography.

The economic record should state exactly what change is being evaluated.

## Economic Basis

Value and cost must use the same economic basis.

For example:

```text
Increment:
Additional 1,000 eligible inquiries / month

Value:
Additional contribution from those 1,000 inquiries

Cost:
Additional customer cost caused by serving those 1,000 inquiries
```

Do not compare:

```text
monthly incremental value
-
single evaluation-run cost
```

or other mismatched populations or time periods.

## Incremental Value

Incremental value is the additional economic benefit caused by the proposed change.

```text
Value after change
-
Value without change
=
Incremental Value
```

For Contoso, a future evidence-backed example could be:

```text
Additional Eligible Volume
        ×
Incremental Conversion Lift
        ×
Observed Average Order Value
        ×
Contribution Margin
        ↓
Incremental Contribution
```

This should remain Unknown until the required evidence exists.

## Incremental Cost

Incremental cost includes costs that change because the proposed investment is made.

Potential examples:

- additional model inference,
- additional Search/tool consumption,
- new capacity tiers,
- additional infrastructure,
- additional observability,
- human review or escalation,
- additional operational support,
- incremental governance or compliance work,
- implementation required specifically for the expansion.

## What Is Not Automatically Incremental Cost

A cost already incurred does not automatically belong in the next-dollar decision.

Examples may include:

- sunk development work,
- existing fixed infrastructure that does not change,
- historical evaluation costs,
- already-committed capacity that remains unchanged.

The question is:

> Would this cost change because we make the proposed investment?

If not, it may matter to total economics but not to incremental economics.

## Step-Function Costs

Incremental cost is not always smooth.

For example:

```text
0–10,000 interactions
        ↓
existing capacity sufficient
        ↓
low incremental infrastructure cost

10,001st interaction
        ↓
new capacity required
        ↓
large incremental cost step
```

Therefore:

```text
Average Cost
≠
Marginal Cost
```

Scaling assumptions should account for capacity thresholds.

## Incremental Net Economic Value

When both incremental value and incremental cost are defensible and use the same economic basis:

```text
Incremental Net Economic Value
=
Incremental Economic Value
-
Incremental Customer Cost
```

Interpretation:

```text
Positive ΔNEV
```

means the proposed change creates more economic value than the additional cost attributed to that change.

```text
Negative ΔNEV
```

means the proposed change consumes more economic value than it creates.

```text
Unknown ΔNEV
```

means the evidence is insufficient to support the calculation.

A positive or negative value should not by itself determine the eventual portfolio action; evidence confidence, resilience, commercial fit, mandatory controls, and dependency are evaluated later.

## Current Contoso State

Today we have:

```text
Modeled scenario value
        =
Available

Known direct execution cost
        =
Available but partial

Real incremental business value
        =
Unknown

Total incremental customer cost
        =
Unknown

Incremental Net Economic Value
        =
Unknown
```

Therefore the current 134x-style modeled AI Value Multiple must not be interpreted as proof that additional investment has attractive incremental economics.

## Example — Why Historical Economics Can Mislead

Suppose an existing workload produces:

```text
$10,000 contribution
for
$1,000 total cost
```

Historical economics look strong.

Now suppose expansion requires:

```text
Additional value: $2,000

Additional model/tool cost:       $200
New capacity tier:              $1,200
Additional human operations:      $900
                                  ─────
Additional cost:                $2,300
```

Then:

```text
Incremental Net Economic Value
=
$2,000 - $2,300
=
-$300
```

The existing workload can remain economically attractive while the proposed expansion is unattractive.

The reverse can also occur: average historical economics may look expensive while the next increment is highly attractive because fixed costs have already been absorbed.

## Evidence Status

Incremental economics should preserve the status of both sides independently.

### Incremental Value

Possible states:

```text
modeled
observed
incremental_established
unknown
```

### Incremental Cost

Possible states:

```text
partial
complete
unknown
```

Do not collapse them into one confidence score.

## Guardrails

- Define the proposed increment before calculating economics.
- Use the same population, time period, and workload scope for value and cost.
- Do not use historical average cost as incremental cost unless they are demonstrably equivalent.
- Do not automatically include sunk cost in the next-dollar calculation.
- Do not ignore step-function or capacity costs.
- Do not treat existing modeled value as incremental value.
- Do not calculate ΔNEV when either side is materially Unknown.
- Keep incremental economics separate from the eventual portfolio action.

## Key Takeaways

- Historical value does not automatically justify additional investment.
- The next-dollar question requires its own economic model.
- Incremental value and incremental cost must be caused by the same proposed change.
- Average and marginal economics can differ materially.
- Fixed and step-function costs can make scale economics nonlinear.
- Sunk cost and incremental cost answer different questions.
- Positive incremental economics are important but are not sufficient by themselves to determine the final investment action.

## Next Step

Create an Incremental Economics Record that makes the proposed change, economic basis, additional value, additional cost, and evidence gaps explicit without manufacturing a next-dollar conclusion when those inputs are Unknown.