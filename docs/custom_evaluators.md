---
title: Custom Evaluators for Contoso Coffee
description: Implementation reference for the project's Foundry custom evaluators.
---

## Custom Evaluators for the Contoso Coffee Agent

> Implementation reference. See the [README](../README.md) and
> [architecture overview](architecture.md) for the current framework.

This document explains the two custom evaluators used by the project:

- `contoso_behavior_rubric`
- `contoso_scope_adherence`

They answer two complementary questions:

```text
contoso_behavior_rubric
        ↓
Did the agent do the task correctly?

contoso_scope_adherence
        ↓
Did the agent stay within the Contoso Coffee domain?
```

Together, they define the quality contract used by the evaluation harness and CI regression gate.

---

## Why Custom Evaluators?

Generic evaluators such as coherence or relevance can be useful, but they do not fully capture the product-specific behavior expected from this agent.

The Contoso Coffee assistant must:

- retrieve menu facts correctly,
- respect price and budget constraints,
- make grounded recommendations,
- avoid inventing unavailable items or prices,
- abstain when the menu does not contain enough information,
- handle ambiguity sensibly,
- stay within Contoso Coffee scope.

A fluent answer can still be wrong for the product.

For example:

```text
Question:
Which drinks are sugar-free?

Plausible but unsupported answer:
Espresso and Americano are sugar-free.
```

If the menu does not provide enough sugar information, the correct behavior is to say that the available data is insufficient.

That is why the evaluation contract needs to measure application behavior, not just writing quality.

---

# 1. `contoso_behavior_rubric`

## Purpose

`contoso_behavior_rubric` is the primary semantic quality evaluator.

It asks:

> **Did the agent satisfy the expected behavior for this test case without introducing unsupported menu facts?**

It is an LLM-as-judge / prompt-based rubric evaluator.

For each regression case, the judge considers inputs such as:

```text
query
ground_truth
agent response
```

and decides whether the generated response satisfies the intended behavior.

## What the rubric checks

A response should pass when it:

- answers the menu question correctly,
- remains grounded in menu information,
- respects constraints in the query,
- does not invent facts,
- abstains when evidence is insufficient,
- handles subjective or ambiguous requests appropriately,
- behaves consistently with the expected behavior captured in `ground_truth`.

The evaluator is intentionally semantic rather than exact-string based.

For example, these should both be acceptable:

```text
A Caramel Macchiato is $5.00.
```

```text
The Caramel Macchiato costs $5.
```

The wording differs, but the behavior is equivalent.

---

## Example — Exact Retrieval

```json
{
  "name": "exact_caramel_macchiato_price",
  "category": "exact_retrieval",
  "query": "How much is a Caramel Macchiato?",
  "ground_truth": "Caramel Macchiato costs $5.00."
}
```

Expected behavior:

```text
Retrieve menu item
      ↓
Return $5.00
      ↓
Do not invent additional facts
      ↓
PASS
```

---

## Example — Abstention

```json
{
  "name": "abstain_sugar_free",
  "category": "abstention",
  "query": "Which drinks are sugar-free?",
  "ground_truth": "The menu does not provide enough sugar information to identify sugar-free drinks. The assistant should avoid making unsupported dietary claims."
}
```

A response such as:

```text
Espresso and Americano are sugar-free.
```

should fail because it makes an unsupported dietary claim.

A response such as:

```text
The menu does not include enough sugar information for me to reliably identify sugar-free drinks.
```

should pass.

This is one reason a product-specific rubric is more useful than a generic coherence score.

---

## Example — Hallucination Resistance

```json
{
  "name": "hallucination_avocado_toast",
  "category": "hallucination_resistance",
  "query": "I'd like the avocado toast. How much is it?",
  "ground_truth": "Avocado toast is not listed in the menu. The assistant should not invent the item or a price."
}
```

Expected behavior:

```text
Requested item not found
      ↓
Say it is not listed
      ↓
Do not invent a price
      ↓
PASS
```

---

## Example — Ambiguity

```json
{
  "name": "ambiguity_best_drink",
  "category": "ambiguity",
  "query": "What's the best drink on the menu?",
  "ground_truth": "There is no objectively best drink in the menu data. The assistant should either ask about preferences or make a clearly qualified recommendation rather than presenting one item as objectively best."
}
```

This checks whether the agent handles subjective questions appropriately instead of presenting an unsupported opinion as fact.

---

# 2. `contoso_scope_adherence`

## Purpose

`contoso_scope_adherence` checks a narrower product rule:

> **Did the assistant remain within the Contoso Coffee domain?**

A response can be fluent and factually correct while still violating the intended product scope.

For example:

```text
User:
What's the weather like in Seattle today?

Agent:
It is 72°F and sunny.
```

Even if the weather answer were correct, answering it would violate the agent's scope.

The expected behavior is to decline or redirect to Contoso Coffee topics.

## Example

```json
{
  "name": "scope_unrelated_weather",
  "category": "scope",
  "query": "What's the weather like in Seattle today?",
  "ground_truth": "The assistant should not answer the unrelated weather question and should politely redirect to Contoso Coffee shop topics."
}
```

Expected behavior:

```text
Unrelated question
      ↓
Do not answer the unrelated request
      ↓
Redirect to Contoso Coffee/menu topics
      ↓
PASS
```

---

# Why Use Two Evaluators?

The evaluators measure different failure modes.

| Evaluator | Question | Signal |
|---|---|---|
| `contoso_behavior_rubric` | Did the agent perform the task correctly? | Semantic/product quality |
| `contoso_scope_adherence` | Did the agent remain within its allowed domain? | Product guardrail |

Keeping them separate makes failures easier to diagnose.

For example:

```text
Behavior rubric     PASS
Scope adherence     FAIL
```

could mean the answer itself was well formed, but the agent answered something outside its job.

Conversely:

```text
Behavior rubric     FAIL
Scope adherence     PASS
```

could mean the agent stayed on topic but gave the wrong menu answer.

---

# How They Fit into the Evaluation Pipeline

The evaluation flow is:

```text
Curated JSONL regression dataset
        ↓
Run Prompt Agent
        ↓
Capture generated responses
        ↓
Run Foundry evaluation
        ↓
contoso_behavior_rubric
+
contoso_scope_adherence
        ↓
Pass rates
        ↓
CI quality gate
```

The project treats the evaluator thresholds as quality gates.

Conceptually:

```text
Behavior pass rate
    >= configured threshold

AND

Scope adherence
    >= configured threshold
```

For example:

```text
BEHAVIOR_PASS_RATE_THRESHOLD = 0.90
SCOPE_PASS_RATE_THRESHOLD    = 1.00
```

The important design principle is:

> **Quality metrics may gate a build. Business-economics assumptions should not.**

Conversion rate, average order value, or contribution margin are business-model inputs and should not cause a pull request to fail.

---

# Why Evaluation Is Part of Tokenomics

Evaluation is directly connected to token economics.

Suppose two agents have the same raw cost:

```text
Agent A
Cost / interaction = $0.01
Success rate        = 95%

Agent B
Cost / interaction = $0.01
Success rate        = 50%
```

Raw token cost makes them look identical.

But:

```text
Cost per successful resolution
=
Cost per interaction
÷
Success rate
```

So:

```text
Agent A
$0.01 / 95%
≈ $0.0105 per successful resolution

Agent B
$0.01 / 50%
= $0.02 per successful resolution
```

Agent B is almost twice as expensive per successful outcome.

That is why the token-to-value flow is:

```text
Tokens
   ↓
Cost
   ↓
Measured quality
   ↓
Cost per successful outcome
   ↓
Business economics
```

A token only becomes economically useful when it contributes to behavior that meets the product's quality bar.

---

# Dataset Design Matters

The evaluator is only as useful as the cases it receives.

The regression dataset should cover multiple behavior categories, such as:

```text
exact retrieval
filtering
arithmetic
semantic recommendation
abstention
hallucination resistance
ambiguity
scope
```

It should also include difficult but valid cases that reveal architectural weaknesses.

Examples include:

```text
exhaustive retrieval
range filtering across many records
aggregation
duplicate handling
multi-item reasoning
```

These are more valuable than intentionally incorrect ground truth.

The purpose is not to force failures.

It is to discover:

> **Where is this architecture reliable, and where does it stop being reliable?**

---

# Custom Evaluator Design Principles

## Evaluate the product contract

Do not ask only:

> Is the answer coherent?

Ask:

> Did the agent behave the way this application requires?

## Prefer semantic behavior over exact wording

Natural-language agents can express the same correct answer in many ways. Use exact matching only when the exact value itself is the requirement.

## Keep narrow guardrails visible

A product rule such as scope adherence deserves its own metric so it is easy to diagnose and gate.

## Test abstention explicitly

Knowing when not to answer is part of correct behavior.

Unsupported certainty should not receive credit merely because the answer sounds plausible.

## Use real failure cases

Do not intentionally corrupt `ground_truth` just to produce a failing score.

Add legitimate difficult cases that expose limitations in retrieval, aggregation, filtering, or reasoning.

## Evaluate the evaluator too

An evaluator can itself be poorly aligned.

When a result seems surprising:

```text
Inspect test case
      ↓
Inspect agent response
      ↓
Inspect evaluator result
      ↓
Decide whether the agent or evaluator is wrong
```

Do not optimize blindly against a score.

---

# Built-In vs. Custom Evaluators

Built-in evaluators are useful for broad dimensions such as:

```text
coherence
relevance
fluency
safety
```

Custom evaluators become important when the application has its own behavioral contract.

For this project:

```text
Do not invent menu facts.
Stay within Contoso Coffee scope.
Abstain when evidence is insufficient.
```

are application-specific requirements.

The general lesson is:

> **Choose evaluators based on the failure modes that matter to the product.**

---

# Interpreting Scores Correctly

Suppose an evaluation run reports:

```text
Behavior rubric      95%
Scope adherence     100%
```

That means the current curated benchmark achieved those pass rates.

It does **not** prove:

```text
The production agent is 95% accurate.
```

The benchmark becomes more representative over time through:

```text
curated regression cases
        +
production traces
        +
newly discovered failures
        ↓
stronger evaluation dataset
```

A valuable production failure should eventually become a regression case.

---

# Evaluation as a Development Loop

```text
Build or modify agent
        ↓
Run regression suite
        ↓
Inspect failures
        ↓
Find root cause
        ↓
Improve prompt / retrieval / model / architecture
        ↓
Run the same suite again
```

Over time:

```text
Production failure
        ↓
Regression case
        ↓
Future change cannot silently reintroduce it
```

This turns evaluation into a software-engineering discipline rather than a one-time benchmark.

---

# Relationship to the Agent Development Lifecycle

```text
Build
  ↓
Prompt Agent + Azure AI Search

Observe
  ↓
Traces

Evaluate
  ↓
contoso_behavior_rubric
+
contoso_scope_adherence

Optimize
  ↓
Improve agent behavior

Monitor
  ↓
Track quality over time

Automate
  ↓
CI regression gate

Measure Economics
  ↓
Quality-adjusted token economics
```

The evaluators provide the bridge between:

```text
The agent produced an answer.
```

and:

```text
The agent produced an outcome we are willing to count as successful.
```

---

# Key Takeaways

```text
contoso_behavior_rubric
=
Did the agent do the job correctly?

contoso_scope_adherence
=
Did the agent stay within its job?
```

Together they make the regression suite meaningful.

The key lessons are:

1. Evaluate application behavior, not only language quality.
2. Keep semantic quality and product guardrails distinguishable.
3. Treat abstention and hallucination resistance as first-class behaviors.
4. Use real difficult cases rather than artificial incorrect ground truth.
5. Feed measured quality into token economics instead of treating every token as equally valuable.

> **A token only becomes economically useful when it contributes to an interaction that meets the product's quality bar.**
