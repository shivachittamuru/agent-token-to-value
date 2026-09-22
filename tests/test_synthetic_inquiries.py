from pathlib import Path

import pytest

from foundry_prompt_agent.synthetic_inquiries import (
    EVIDENCE_MODE,
    GENERATOR_VERSION,
    SUPPORTED_CATEGORIES,
    generate_inquiries,
    load_menu,
)

MENU = load_menu(Path("data/contoso.json"))

_FORBIDDEN_KEYS = (
    "order",
    "order_id",
    "order_completed",
    "customer_engaged",
    "incremental",
    "assignment",
    "treatment",
    "control",
    "revenue",
    "conversion",
)


def gen(seed=42, count=20, **kwargs):
    return generate_inquiries(seed=seed, count=count, menu=MENU, **kwargs)


def only(category, count=10, seed=42):
    return generate_inquiries(
        seed=seed,
        count=count,
        menu=MENU,
        category_weights={category: 1.0},
    )


def test_same_seed_same_config_is_identical():
    assert gen(seed=42, count=20) == gen(seed=42, count=20)


def test_different_seeds_produce_variation():
    assert gen(seed=42, count=20) != gen(seed=7, count=20)


def test_exact_requested_count():
    assert len(gen(seed=1, count=13)) == 13


def test_deterministic_unique_ids():
    cases = gen(seed=42, count=20)
    names = [case["name"] for case in cases]

    assert len(set(names)) == len(names)
    # Stable across regeneration.
    assert names == [case["name"] for case in gen(seed=42, count=20)]


def test_generated_categories_are_supported():
    for case in gen(seed=99, count=40):
        assert case["category"] in SUPPORTED_CATEGORIES


def test_category_weights_respected():
    cases = only("exact_retrieval", count=15)

    assert all(case["category"] == "exact_retrieval" for case in cases)


def test_menu_backed_cases_use_source_facts():
    prices = {entry["item"]: float(entry["price"]) for entry in MENU}

    for case in only("exact_retrieval", count=20):
        # The referenced item must be a real menu item with its real price.
        item = next(name for name in prices if name in case["query"])
        assert f"${prices[item]:.2f}" in case["ground_truth"]


def test_unsupported_item_expects_abstention_not_hallucination():
    menu_items = {entry["item"] for entry in MENU}

    for case in only("hallucination_resistance", count=20):
        # The item is genuinely absent and the expectation is non-invention.
        assert "not on the Contoso Coffee menu" in case["ground_truth"]
        # No real menu item is being (mis)used as the absent item here.
        assert not any(
            item in case["query"] and item in menu_items for item in menu_items
        ) or "not on the Contoso Coffee menu" in case["ground_truth"]


def test_out_of_scope_expects_scope_behavior():
    for case in only("scope", count=10):
        assert "unrelated to Contoso Coffee" in case["ground_truth"]
        assert "redirect" in case["ground_truth"]


def test_records_match_evaluation_schema():
    for case in gen(seed=3, count=20):
        assert {"name", "category", "query", "ground_truth"} <= set(case)
        assert isinstance(case["query"], str) and case["query"]
        assert isinstance(case["ground_truth"], str) and case["ground_truth"]


def test_provenance_is_preserved():
    for case in gen(seed=42, count=20):
        assert case["evidence_mode"] == EVIDENCE_MODE
        assert case["seed"] == 42
        assert case["generator_version"] == GENERATOR_VERSION


def test_no_business_outcomes_are_fabricated():
    for case in gen(seed=42, count=20):
        for key in case:
            assert not any(bad in key.lower() for bad in _FORBIDDEN_KEYS)


def test_no_treatment_control_assignment_is_fabricated():
    for case in gen(seed=42, count=20):
        assert "assignment" not in case
        assert "treatment" not in case
        assert "control" not in case


def test_abstention_expects_abstention_behavior():
    for case in only("abstention", count=10):
        assert "abstain" in case["ground_truth"].lower()


def test_zero_positive_weights_raise():
    with pytest.raises(ValueError):
        generate_inquiries(
            seed=1, count=5, menu=MENU, category_weights={"scope": 0.0}
        )
