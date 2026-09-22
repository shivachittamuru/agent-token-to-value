"""Seeded synthetic inquiry generator for the Contoso workload simulator.

Generates reproducible, variable customer inquiries as evaluation-ready cases
that match the schema in ``evals/contoso_agent_eval_v3.jsonl`` (name, category,
query, ground_truth). Generation is fully deterministic for a given seed and
configuration, uses a local ``random.Random`` instance (never global state),
and does not use an LLM.

This module only produces synthetic *customer inputs*. It never creates orders,
customer engagement, treatment/control assignment, or any business outcome.
Real evidence still comes from the real agent and real evaluation downstream.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

GENERATOR_VERSION = "1"
EVIDENCE_MODE = "synthetic_simulation"

SUPPORTED_CATEGORIES = (
    "exact_retrieval",
    "filtering",
    "arithmetic",
    "semantic_recommendation",
    "ambiguity",
    "abstention",
    "hallucination_resistance",
    "scope",
    "exhaustive_retrieval",
)

# Attributes the menu does not describe; the agent should abstain, not invent.
_UNSUPPORTED_ATTRIBUTES = (
    "sugar-free",
    "gluten-free",
    "dairy-free",
    "vegan",
    "keto-friendly",
    "nut-free",
)

# Items that are plausible but deliberately absent from the Contoso menu.
_ABSENT_ITEMS = (
    "Avocado Toast",
    "Bacon Cheeseburger",
    "French Fries",
    "Hot Dog",
    "Caesar Salad",
    "Milkshake",
    "Pancakes",
    "Ramen",
)

_OUT_OF_SCOPE_QUESTIONS = (
    "What's the weather like today?",
    "Who won the game last night?",
    "What time is it in Tokyo?",
    "Can you help me book a flight?",
    "What's the capital of France?",
    "Can you recommend a good movie?",
)

# Descriptive keywords used for semantic recommendations; only keywords with at
# least one menu match are used, so the expected behavior stays defensible.
_SEMANTIC_KEYWORDS = (
    "strong",
    "rich",
    "creamy",
    "sweet",
    "chocolate",
    "classic",
    "refreshing",
    "fruity",
)

_EXACT_TEMPLATES = (
    "How much is a {item}?",
    "What does the {item} cost?",
    "{item} price?",
    "Can you tell me the price of the {item}?",
)

_FILTERING_TEMPLATES = (
    "Which {category} options do you have?",
    "List the items in the {category} category.",
    "What {category} can I order?",
)

_ARITHMETIC_TEMPLATES = (
    "Can I buy a {a} and a {b} for ${budget}?",
    "If I get a {a} and a {b}, is ${budget} enough?",
    "Would ${budget} cover a {a} and a {b}?",
)

_SEMANTIC_TEMPLATES = (
    "I want something {keyword}. What do you recommend?",
    "Which option is {keyword}?",
    "I'm in the mood for a {keyword} choice.",
)

_AMBIGUITY_TEMPLATES = (
    "What's the best {category} you have?",
    "Which {category} is the best?",
    "What's your best {category}?",
)

_ABSTENTION_TEMPLATES = (
    "Which items are {attribute}?",
    "Do you have any {attribute} options?",
    "Which drinks are {attribute}?",
)

_HALLUCINATION_TEMPLATES = (
    "I'd like the {item}. How much is it?",
    "Can I get a {item}?",
    "What's the price of your {item}?",
)

_EXHAUSTIVE_TEMPLATES = (
    "List every unique menu item that costs exactly ${price}. "
    "Do not miss any and do not double-count.",
    "Which items cost exactly ${price}? List them all.",
)


def load_menu(path: Path | str) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _price(value: float) -> str:
    return f"${value:.2f}"


class _MenuFacts:
    """Deduplicated, indexed menu facts derived once from the source data."""

    def __init__(self, menu: list[dict]) -> None:
        seen: set[str] = set()
        self.items: list[dict] = []
        for entry in menu:
            name = entry["item"]
            if name in seen:
                continue
            seen.add(name)
            self.items.append(
                {
                    "item": name,
                    "price": float(entry["price"]),
                    "category": entry["category"],
                    "description": entry.get("description", ""),
                }
            )

        self.item_names = {item["item"] for item in self.items}

        self.by_category: dict[str, list[str]] = {}
        for item in self.items:
            self.by_category.setdefault(item["category"], []).append(item["item"])

        self.by_price: dict[float, list[str]] = {}
        for item in self.items:
            self.by_price.setdefault(item["price"], []).append(item["item"])

        self.semantic: dict[str, list[str]] = {}
        for keyword in _SEMANTIC_KEYWORDS:
            matches = [
                item["item"]
                for item in self.items
                if keyword in item["description"].lower()
            ]
            if matches:
                self.semantic[keyword] = matches


def _build_exact(rng: random.Random, facts: _MenuFacts) -> tuple[str, str]:
    item = rng.choice(facts.items)
    query = rng.choice(_EXACT_TEMPLATES).format(item=item["item"])
    ground_truth = f"{item['item']} costs {_price(item['price'])}."
    return query, ground_truth


def _build_filtering(rng: random.Random, facts: _MenuFacts) -> tuple[str, str]:
    category = rng.choice(sorted(facts.by_category))
    items = sorted(facts.by_category[category])
    query = rng.choice(_FILTERING_TEMPLATES).format(category=category)
    ground_truth = (
        f"The {category} items are: {', '.join(items)}."
    )
    return query, ground_truth


def _build_arithmetic(rng: random.Random, facts: _MenuFacts) -> tuple[str, str]:
    first, second = rng.sample(facts.items, 2)
    total = first["price"] + second["price"]
    budget = round(total + rng.choice([-1.0, -0.5, 0.0, 0.5, 1.0]), 2)
    query = rng.choice(_ARITHMETIC_TEMPLATES).format(
        a=first["item"], b=second["item"], budget=f"{budget:.2f}"
    )
    if budget >= total:
        ground_truth = (
            f"Yes. {first['item']} costs {_price(first['price'])} and "
            f"{second['item']} costs {_price(second['price'])}, for a total of "
            f"{_price(total)}, which is within {_price(budget)}."
        )
    else:
        ground_truth = (
            f"No. {first['item']} ({_price(first['price'])}) plus "
            f"{second['item']} ({_price(second['price'])}) totals "
            f"{_price(total)}, which exceeds {_price(budget)}."
        )
    return query, ground_truth


def _build_semantic(rng: random.Random, facts: _MenuFacts) -> tuple[str, str]:
    keyword = rng.choice(sorted(facts.semantic))
    matches = sorted(facts.semantic[keyword])
    query = rng.choice(_SEMANTIC_TEMPLATES).format(keyword=keyword)
    ground_truth = (
        f"Items described as {keyword} include: {', '.join(matches)}. "
        "The assistant should recommend from these menu-supported matches."
    )
    return query, ground_truth


def _build_ambiguity(rng: random.Random, facts: _MenuFacts) -> tuple[str, str]:
    category = rng.choice(sorted(facts.by_category))
    query = rng.choice(_AMBIGUITY_TEMPLATES).format(category=category)
    ground_truth = (
        f"There is no objectively best {category} in the menu data. The "
        "assistant should ask about preferences or give a clearly qualified "
        "recommendation rather than naming one as objectively best."
    )
    return query, ground_truth


def _build_abstention(rng: random.Random, facts: _MenuFacts) -> tuple[str, str]:
    attribute = rng.choice(_UNSUPPORTED_ATTRIBUTES)
    query = rng.choice(_ABSTENTION_TEMPLATES).format(attribute=attribute)
    ground_truth = (
        f"The menu does not include {attribute} information, so the assistant "
        "should abstain rather than make unsupported claims."
    )
    return query, ground_truth


def _build_hallucination(
    rng: random.Random, facts: _MenuFacts
) -> tuple[str, str]:
    # Only use items genuinely absent from the source menu.
    candidates = [name for name in _ABSENT_ITEMS if name not in facts.item_names]
    item = rng.choice(candidates)
    query = rng.choice(_HALLUCINATION_TEMPLATES).format(item=item)
    ground_truth = (
        f"{item} is not on the Contoso Coffee menu. The assistant should not "
        "invent the item or a price and should say it is unavailable."
    )
    return query, ground_truth


def _build_scope(rng: random.Random, facts: _MenuFacts) -> tuple[str, str]:
    query = rng.choice(_OUT_OF_SCOPE_QUESTIONS)
    ground_truth = (
        "This question is unrelated to Contoso Coffee. The assistant should "
        "not answer it and should politely redirect to coffee-shop topics."
    )
    return query, ground_truth


def _build_exhaustive(rng: random.Random, facts: _MenuFacts) -> tuple[str, str]:
    priced = sorted(
        price for price, items in facts.by_price.items() if len(items) >= 2
    )
    price = rng.choice(priced)
    items = sorted(facts.by_price[price])
    query = rng.choice(_EXHAUSTIVE_TEMPLATES).format(price=f"{price:.2f}")
    ground_truth = (
        f"The unique items that cost {_price(price)} are: {', '.join(items)}."
    )
    return query, ground_truth


_BUILDERS = {
    "exact_retrieval": _build_exact,
    "filtering": _build_filtering,
    "arithmetic": _build_arithmetic,
    "semantic_recommendation": _build_semantic,
    "ambiguity": _build_ambiguity,
    "abstention": _build_abstention,
    "hallucination_resistance": _build_hallucination,
    "scope": _build_scope,
    "exhaustive_retrieval": _build_exhaustive,
}


def _category_choices(
    rng: random.Random,
    count: int,
    category_weights: dict | None,
) -> list[str]:
    if category_weights is None:
        weights = [1.0] * len(SUPPORTED_CATEGORIES)
    else:
        weights = [
            float(category_weights.get(category, 0.0))
            for category in SUPPORTED_CATEGORIES
        ]
        if sum(weights) <= 0:
            raise ValueError("category_weights must include a positive weight")

    return rng.choices(list(SUPPORTED_CATEGORIES), weights=weights, k=count)


def generate_inquiries(
    *,
    seed: int,
    count: int,
    menu: list[dict],
    category_weights: dict | None = None,
    generator_version: str = GENERATOR_VERSION,
) -> list[dict]:
    """Generate ``count`` deterministic synthetic inquiry cases for ``seed``.

    Cases are schema-compatible with the evaluation pipeline (name, category,
    query, ground_truth) and carry explicit synthetic provenance. No business
    outcomes or treatment/control assignments are ever produced.
    """

    if count < 0:
        raise ValueError("count must be >= 0")

    rng = random.Random(seed)
    facts = _MenuFacts(menu)
    categories = _category_choices(rng, count, category_weights)

    cases = []
    for index, category in enumerate(categories):
        query, ground_truth = _BUILDERS[category](rng, facts)
        cases.append(
            {
                "name": f"sim_{index:04d}_{category}",
                "category": category,
                "query": query,
                "ground_truth": ground_truth,
                # Explicit synthetic provenance carried on every case.
                "evidence_mode": EVIDENCE_MODE,
                "seed": seed,
                "generator_version": generator_version,
            }
        )

    return cases
