"""Workload Assessment records — structured synthesis, not a score.

This module summarizes what the accumulated evidence establishes, models, or
leaves Unknown across independent dimensions. It never recalculates economics,
never produces a composite score or average confidence, and never selects a
portfolio action (those belong to the DECIDE phase). Each dimension preserves
the evidence state of its source record; strong technical evidence never
promotes weaker business or economic evidence.
"""

from __future__ import annotations

from foundry_prompt_agent.business_outcomes import DOWNSTREAM_FIELDS

TECHNICAL_ESTABLISHED = "established"
TECHNICAL_UNKNOWN = "unknown"

# Provenance of the technical evidence, kept separate from its status.
TECHNICAL_SCOPE_REGRESSION = "regression"
TECHNICAL_SCOPE_SIMULATION = "simulation"

BUSINESS_OUTCOME_OBSERVED = "observed"
BUSINESS_OUTCOME_UNKNOWN = "unknown"

INCREMENTALITY_ESTABLISHED = "established"
INCREMENTALITY_IN_PROGRESS = "in_progress"
INCREMENTALITY_UNKNOWN = "unknown"

ASSESSMENT_INCOMPLETE = "evidence_incomplete_for_investment_decision"
ASSESSMENT_COMPLETE = "evidence_complete_for_investment_decision"


def _technical_performance_status(business_outcome_records: list[dict]) -> str:
    if not business_outcome_records:
        return TECHNICAL_UNKNOWN
    evaluated = sum(
        1 for r in business_outcome_records if r.get("accepted") is not None
    )
    return (
        TECHNICAL_ESTABLISHED
        if evaluated == len(business_outcome_records)
        else TECHNICAL_UNKNOWN
    )


def _business_outcome_status(business_outcome_records: list[dict]) -> str:
    has_evidence = any(
        record.get("outcome_evidence_source") is not None
        or any(record.get(field) is not None for field in DOWNSTREAM_FIELDS)
        for record in business_outcome_records
    )
    return BUSINESS_OUTCOME_OBSERVED if has_evidence else BUSINESS_OUTCOME_UNKNOWN


def _incrementality_status(
    business_outcome_records: list[dict],
    pilot_evidence_records: list[dict],
) -> str:
    has_counterfactual = any(
        r.get("assignment") is not None for r in pilot_evidence_records
    ) or any(
        r.get("counterfactual_method") is not None
        for r in business_outcome_records
    )
    has_incremental = any(
        r.get("incremental_order") is not None
        for r in business_outcome_records
    )

    if has_incremental and has_counterfactual:
        return INCREMENTALITY_ESTABLISHED
    if has_counterfactual:
        return INCREMENTALITY_IN_PROGRESS
    return INCREMENTALITY_UNKNOWN


def build_workload_assessment(
    *,
    workload_id: str,
    execution_economics: dict,
    economic_value: dict,
    incremental_economics: dict,
    value_resilience: dict,
    business_outcome_records: list[dict],
    pilot_evidence_records: list[dict],
    run_mode: str = "regression",
) -> dict:
    """Synthesize existing evidence records into a structured assessment.

    Each dimension preserves its source record's evidence state. No economics
    are recalculated and no portfolio action is selected. ``run_mode`` sets the
    technical evidence scope (regression vs. simulation) without changing the
    technical evidence status.
    """

    technical_performance_status = _technical_performance_status(
        business_outcome_records
    )
    technical_evidence_scope = (
        TECHNICAL_SCOPE_SIMULATION
        if run_mode == "simulation"
        else TECHNICAL_SCOPE_REGRESSION
    )
    execution_cost_status = execution_economics["cost_completeness"]
    business_outcome_status = _business_outcome_status(business_outcome_records)
    incrementality_status = _incrementality_status(
        business_outcome_records, pilot_evidence_records
    )
    economic_value_status = economic_value["value_evidence_status"]
    incremental_economics_status = incremental_economics["economics_status"]
    resilience_scope = value_resilience["resilience_scope"]
    resilience_status = value_resilience["resilience_status"]

    established_claims = []
    if technical_performance_status == TECHNICAL_ESTABLISHED:
        if technical_evidence_scope == TECHNICAL_SCOPE_SIMULATION:
            established_claims.append(
                "Technical behavior established for the simulated workload"
            )
        else:
            established_claims.append(
                "Technical behavior established in the regression suite"
            )
    established_claims.append(
        "Model inference cost measured directly from token usage"
    )

    modeled_claims = []
    if economic_value_status == "modeled_only":
        modeled_claims.append(
            "Recovered contribution and AI Value Multiple are modeled "
            "scenario estimates"
        )
    if resilience_scope == "modeled_scenario":
        modeled_claims.append(
            "Value resilience assessed on modeled scenarios only"
        )

    unknown_claims = []
    if business_outcome_status == BUSINESS_OUTCOME_UNKNOWN:
        unknown_claims.append("Downstream business outcomes not observed")
    if incrementality_status == INCREMENTALITY_UNKNOWN:
        unknown_claims.append("Causal/incremental conversion not established")
    if incremental_economics_status != "incremental_net_value_established":
        unknown_claims.append("Next-dollar (incremental) economics not established")
    if execution_cost_status != "complete":
        unknown_claims.append("Total relevant customer cost incomplete")

    decision_gaps = []
    if business_outcome_status == BUSINESS_OUTCOME_UNKNOWN:
        decision_gaps.append("real eligible-demand baseline")
        decision_gaps.append("real business outcomes")
    if incrementality_status == INCREMENTALITY_UNKNOWN:
        decision_gaps.append("causal/incremental conversion")
    if execution_cost_status != "complete":
        decision_gaps.append("Total Relevant Customer Cost")
    if incremental_economics_status != "incremental_net_value_established":
        decision_gaps.append("next-dollar economics")
    if resilience_scope == "modeled_scenario":
        decision_gaps.append("capacity step-functions")

    next_evidence_priorities = []
    if business_outcome_status == BUSINESS_OUTCOME_UNKNOWN:
        next_evidence_priorities.append("actual eligible-demand baseline")
        next_evidence_priorities.append("observed order economics")
    if incrementality_status == INCREMENTALITY_UNKNOWN:
        next_evidence_priorities.append("treatment/control conversion")
    if execution_cost_status != "complete":
        next_evidence_priorities.append("Total Relevant Customer Cost")
    if resilience_scope == "modeled_scenario":
        next_evidence_priorities.append("realistic-volume capacity behavior")

    assessment_status = (
        ASSESSMENT_INCOMPLETE if decision_gaps else ASSESSMENT_COMPLETE
    )

    return {
        "workload_id": workload_id,
        "technical_performance_status": technical_performance_status,
        "technical_evidence_scope": technical_evidence_scope,
        "execution_cost_status": execution_cost_status,
        "business_outcome_status": business_outcome_status,
        "incrementality_status": incrementality_status,
        "economic_value_status": economic_value_status,
        "incremental_economics_status": incremental_economics_status,
        "resilience_scope": resilience_scope,
        "resilience_status": resilience_status,
        "established_claims": established_claims,
        "modeled_claims": modeled_claims,
        "unknown_claims": unknown_claims,
        "decision_gaps": decision_gaps,
        "next_evidence_priorities": next_evidence_priorities,
        "assessment_status": assessment_status,
    }
