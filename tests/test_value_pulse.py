from foundry_prompt_agent.dashboard_views import build_value_pulse_view


def _summary() -> dict:
    return {
        "run_id": "20261014001708",
        "workload_id": "contoso-demand-recovery",
        "run_mode": "regression",
        "execution_economics": {
            "attempted_interactions": 10,
            "accepted_interactions": 9,
            "acceptance_rate": 0.9,
            "known_direct_cost_per_accepted_work_usd": 0.008,
        },
        "modeled_business_economics": {
            "recovered_orders_per_month": 486,
            "recovered_contribution_per_month": 1701,
            "ai_value_multiple": 131.35,
        },
        "economic_value": {
            "modeled_recovered_contribution_usd": 1701,
            "modeled_ai_value_multiple": 131.35,
            "customer_net_economic_value_usd": None,
        },
        "workload_assessment": {
            "business_outcome_status": "unknown",
            "business_evidence_scope": "regression",
            "economic_value_status": "modeled_only",
        },
        "portfolio_action": {
            "selected_action": "prove",
            "action_rationale": "Production outcomes are not established.",
            "required_evidence": ["Measure observed outcomes."],
        },
    }


def _interactions(count: int = 10) -> list[dict]:
    return [
        {
            "run_mode": "regression",
            "acceptance": {"accepted": index < 9},
            "business_outcome": {},
        }
        for index in range(count)
    ]


def test_compatible_runtime_economics_are_primary_and_keep_labels_distinct():
    summary = _summary()
    summary.update(
        {
            "azure_runtime_cost": {
                "workload_id": "contoso-demand-recovery",
                "allocated_azure_runtime_cost_usd": 52.53,
                "cost_period": {"start": "2026-09-01", "end": "2026-09-30"},
                "evidence_source": {"evidence_status": "observed_billing"},
            },
            "azure_runtime_modeled_economics": {
                "modeled_contribution_after_azure_runtime_usd": 1648.47,
                "modeled_azure_runtime_value_multiple": 32.38,
            },
        }
    )

    pulse = build_value_pulse_view(summary, _interactions())

    assert pulse["context"]["period"] == "Sep 2026"
    assert pulse["measure"]["system_cost_usd"] == 52.53
    assert pulse["measure"]["cost_per_accepted_work_usd"] == 0.008
    assert pulse["measure"]["cost_per_accepted_work_basis"] == "Run inference cost"
    assert pulse["value"]["value_multiple_label"] == (
        "Modeled Azure Runtime Value Multiple"
    )
    assert pulse["value"]["value_multiple"] == 32.38
    assert pulse["value"]["economic_value_usd"] == 1648.47
    assert "inference-only" not in pulse["value"]["value_multiple_label"].lower()


def test_no_runtime_snapshot_uses_explicit_inference_only_economics():
    pulse = build_value_pulse_view(_summary(), _interactions())

    assert pulse["measure"]["system_cost_usd"] is None
    assert pulse["value"]["value_multiple_label"] == (
        "Modeled AI Value Multiple (inference-only)"
    )
    assert pulse["value"]["value_multiple"] == 131.35


def test_modeled_outcome_is_not_presented_as_observed():
    pulse = build_value_pulse_view(_summary(), _interactions())

    assert pulse["outcome"]["evidence_type"] == "MODELED"
    assert pulse["outcome"]["primary_metric_label"] == (
        "Modeled recovered orders / month"
    )
    assert pulse["outcome"]["production_status"] == "Not observed"


def test_simulated_outcomes_are_explicitly_labeled():
    summary = _summary()
    summary.update(
        {
            "run_mode": "simulation",
            "synthetic_experiment": {"simulated_conversion_lift_pp": 12.5},
            "synthetic_economics": {
                "simulated_incremental_orders_for_observed_sample": 2
            },
        }
    )

    pulse = build_value_pulse_view(summary, _interactions())

    assert pulse["outcome"]["evidence_type"] == "SIMULATED"
    assert pulse["outcome"]["primary_metric_value"] == 12.5
    assert pulse["outcome"]["magnitude_value"] == 2
    assert pulse["outcome"]["production_status"] == "Not established"


def test_simulation_scope_is_never_presented_as_production_evidence():
    summary = _summary()
    summary["workload_assessment"]["business_evidence_scope"] = "simulation"

    pulse = build_value_pulse_view(summary, _interactions())

    assert pulse["outcome"]["evidence_type"] == "SIMULATED"
    assert pulse["outcome"]["production_status"] == "Not established"


def test_missing_outcome_and_optional_fields_remain_unknown():
    summary = {
        "run_id": "run-without-timestamp",
        "workload_id": "unknown-workload",
    }

    pulse = build_value_pulse_view(summary, [])

    assert pulse["outcome"]["evidence_type"] == "UNKNOWN"
    assert pulse["outcome"]["primary_metric_value"] is None
    assert pulse["value"]["evidence_confidence"] == "UNKNOWN"
    assert pulse["measure"]["accepted_work_count"] is None
    assert pulse["action"]["selected_action"] == "UNKNOWN"
    assert pulse["context"]["period"] == "run-without-timestamp"


def test_customer_economics_stay_not_established_without_complete_evidence():
    pulse = build_value_pulse_view(_summary(), _interactions())

    assert pulse["context"]["customer_economics_status"] == "Not established"
    assert pulse["value"]["customer_economics_status"] == "Not established"


def test_action_rationale_and_next_evidence_are_reused():
    pulse = build_value_pulse_view(_summary(), _interactions())

    assert pulse["action"]["selected_action"] == "PROVE"
    assert pulse["action"]["rationale"] == (
        "Production outcomes are not established."
    )
    assert pulse["action"]["next_step"] == "Measure observed outcomes."


def test_incompatible_runtime_cost_is_not_used_or_divided_by_run_work():
    summary = _summary()
    summary["azure_runtime_cost"] = {
        "workload_id": "different-workload",
        "allocated_azure_runtime_cost_usd": 900,
        "cost_period": {"start": "2026-09-01", "end": "2026-09-30"},
    }
    summary["execution_economics"].pop(
        "known_direct_cost_per_accepted_work_usd"
    )

    pulse = build_value_pulse_view(summary, _interactions())

    assert pulse["measure"]["system_cost_usd"] is None
    assert pulse["measure"]["cost_per_accepted_work_usd"] is None
    assert pulse["measure"]["cost_per_accepted_work_basis"] == "Not established"
    assert pulse["value"]["value_multiple_label"] == (
        "Modeled AI Value Multiple (inference-only)"
    )


def test_observed_outcome_records_are_labeled_and_summarized_as_observed():
    summary = _summary()
    summary["workload_assessment"].update(
        {
            "business_outcome_status": "observed",
            "business_evidence_scope": "production",
        }
    )
    interactions = [
        {
            "run_mode": "regression",
            "business_outcome": {
                "outcome_evidence_source": "production_crm",
                "order_completed": True,
                "order_value_usd": 12.5,
            },
        },
        {
            "run_mode": "regression",
            "business_outcome": {
                "outcome_evidence_source": "production_crm",
                "order_completed": False,
                "order_value_usd": None,
            },
        },
    ]

    pulse = build_value_pulse_view(summary, interactions)

    assert pulse["outcome"]["evidence_type"] == "OBSERVED"
    assert pulse["outcome"]["primary_metric_value"] == 1
    assert pulse["outcome"]["magnitude_value"] == 12.5
