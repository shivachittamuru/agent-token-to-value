"""Value Resilience records — modeled scenario sensitivity only.

Value Resilience asks how much important modeled economic drivers can
deteriorate before the economic conclusion changes. The current Contoso
workload has only modeled scenario economics, so this module assesses
*modeled scenario* resilience — never realized, causal, incremental, or
production resilience.

Scenario economics are computed with the existing ``business_economics``
functions; no formulas are duplicated here. Structural risks that cannot be
expressed as parameter stress are tracked separately as explicit Unknowns and
never converted into stress percentages or probabilities.
"""

from __future__ import annotations

from foundry_prompt_agent.business_economics import scenario_from_measured_run

RESILIENCE_SCOPE = "modeled_scenario"
VALUE_EVIDENCE_MODELED_ONLY = "modeled_only"
RESILIENCE_NOT_CLASSIFIED = "not_classified"

# Economic conclusion boundary: modeled contribution covers inference cost.
CONCLUSION_VALUE_MULTIPLE_THRESHOLD = 1.0

DRIVER_KEYS = (
    "conversion_rate",
    "average_order_value_usd",
    "contribution_margin",
)

STRUCTURAL_UNKNOWNS = (
    "real incremental conversion not established",
    "real eligible demand baseline not established",
    "total relevant customer cost incomplete",
    "human/recovery economics incomplete",
    "capacity step-functions not established",
)


def _build_scenario(
    name: str,
    measured_run: dict,
    scenario_assumptions: dict,
    cost_stress_multiplier: float,
    changed_inputs: dict,
) -> dict:
    economics = scenario_from_measured_run(
        measured_run,
        scenario_assumptions,
        cost_stress_multiplier=cost_stress_multiplier,
    )
    return {
        "scenario": name,
        "changed_inputs": changed_inputs,
        # Exact assumptions used for this scenario, preserved verbatim.
        "assumptions": dict(scenario_assumptions),
        "cost_stress_multiplier": cost_stress_multiplier,
        "modeled_recovered_contribution_usd": economics[
            "recovered_contribution_per_month"
        ],
        "modeled_ai_value_multiple": economics["ai_value_multiple"],
        "break_even_conversion_rate": economics["break_even_conversion_rate"],
    }


def _expand_scenarios(
    measured_run: dict,
    assumptions: dict,
    stress_spec: dict,
) -> list[dict]:
    scenarios: list[dict] = []

    for key in DRIVER_KEYS:
        for value in stress_spec.get(key, []):
            scenarios.append(
                _build_scenario(
                    f"{key}={value}",
                    measured_run,
                    {**assumptions, key: value},
                    1.0,
                    {key: value},
                )
            )

    for multiplier in stress_spec.get("cost_stress_multiplier", []):
        scenarios.append(
            _build_scenario(
                f"cost_stress_multiplier={multiplier}",
                measured_run,
                assumptions,
                multiplier,
                {"cost_stress_multiplier": multiplier},
            )
        )

    for combo in stress_spec.get("combined", []):
        combo = dict(combo)
        name = combo.pop("name", "combined")
        cost_stress_multiplier = combo.pop("cost_stress_multiplier", 1.0)
        changed_inputs = dict(combo)
        if cost_stress_multiplier != 1.0:
            changed_inputs["cost_stress_multiplier"] = cost_stress_multiplier
        scenarios.append(
            _build_scenario(
                name,
                measured_run,
                {**assumptions, **combo},
                cost_stress_multiplier,
                changed_inputs,
            )
        )

    return scenarios


def build_value_resilience_record(
    *,
    workload_id: str,
    measured_run: dict,
    assumptions: dict,
    stress_spec: dict | None = None,
) -> dict:
    """Build one modeled-scenario Value Resilience record.

    A base case is computed from the existing business economics, optional
    transparent stress scenarios vary important modeled drivers, and drivers
    whose adverse change flips the economic conclusion are surfaced
    descriptively. The workload is never auto-classified as resilient/fragile.
    """

    base_case = _build_scenario("base", measured_run, assumptions, 1.0, {})
    scenarios = (
        _expand_scenarios(measured_run, assumptions, stress_spec)
        if stress_spec
        else []
    )

    base_multiple = base_case["modeled_ai_value_multiple"]
    decision_sensitive_drivers: list[str] = []
    if base_multiple >= CONCLUSION_VALUE_MULTIPLE_THRESHOLD:
        sensitive: set[str] = set()
        for scenario in scenarios:
            if (
                scenario["modeled_ai_value_multiple"]
                < CONCLUSION_VALUE_MULTIPLE_THRESHOLD
            ):
                sensitive.update(scenario["changed_inputs"].keys())
        decision_sensitive_drivers = sorted(sensitive)

    return {
        "workload_id": workload_id,
        "resilience_scope": RESILIENCE_SCOPE,
        "value_evidence_status": VALUE_EVIDENCE_MODELED_ONLY,
        "base_case": base_case,
        "stress_scenarios": scenarios,
        "decision_sensitive_drivers": decision_sensitive_drivers,
        "resilience_status": RESILIENCE_NOT_CLASSIFIED,
        "structural_unknowns": list(STRUCTURAL_UNKNOWNS),
    }
