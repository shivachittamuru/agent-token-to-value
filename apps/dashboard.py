"""Interactive token-economics dashboard for the Contoso Coffee agent.

Run from the repository root:
    uv run streamlit run apps/dashboard.py

The dashboard never calls the agent or Foundry. It reads measured evaluation
runs from evals/tokenomics_history.jsonl and recomputes business scenarios
locally with summarize_business_economics().
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from foundry_prompt_agent import dashboard_views
from foundry_prompt_agent import history
from foundry_prompt_agent.business_economics import (
    conversion_sensitivity,
    scenario_from_measured_run,
)
from foundry_prompt_agent.cost_snapshot import load_cost_snapshot

COST_SNAPSHOTS_DIR = Path("cost_snapshots")
WORKLOAD_ID = "contoso-demand-recovery"


PRESETS = {
    "Conservative": {
        "missed_contacts": 50,
        "ai_eligible_pct": 40,
        "conversion_pct": 5,
        "average_order_value": 8.0,
        "contribution_margin_pct": 30,
        "cost_stress_multiplier": 10.0,
    },
    "Base Case": {
        "missed_contacts": 100,
        "ai_eligible_pct": 60,
        "conversion_pct": 20,
        "average_order_value": 10.0,
        "contribution_margin_pct": 35,
        "cost_stress_multiplier": 3.0,
    },
    "Optimistic": {
        "missed_contacts": 150,
        "ai_eligible_pct": 70,
        "conversion_pct": 30,
        "average_order_value": 12.0,
        "contribution_margin_pct": 40,
        "cost_stress_multiplier": 1.0,
    },
}


def money(value: float, digits: int = 2) -> str:
    return f"${value:,.{digits}f}"


def initialize_scenario_state(latest: dict) -> None:
    """Initialize editable scenario controls from the latest measured run."""
    defaults = {
        "missed_contacts": int(latest["missed_contacts_per_day"]),
        "ai_eligible_pct": int(round(latest["ai_eligible_rate"] * 100)),
        "conversion_pct": int(round(latest["conversion_rate"] * 100)),
        "average_order_value": float(latest["average_order_value_usd"]),
        "contribution_margin_pct": int(
            round(latest["contribution_margin"] * 100)
        ),
        "cost_stress_multiplier": 1.0,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def apply_preset(name: str) -> None:
    for key, value in PRESETS[name].items():
        st.session_state[key] = value


def reset_to_latest(latest: dict) -> None:
    st.session_state["missed_contacts"] = int(
        latest["missed_contacts_per_day"]
    )
    st.session_state["ai_eligible_pct"] = int(
        round(latest["ai_eligible_rate"] * 100)
    )
    st.session_state["conversion_pct"] = int(
        round(latest["conversion_rate"] * 100)
    )
    st.session_state["average_order_value"] = float(
        latest["average_order_value_usd"]
    )
    st.session_state["contribution_margin_pct"] = int(
        round(latest["contribution_margin"] * 100)
    )
    st.session_state["cost_stress_multiplier"] = 1.0


def calculate_scenario(measured: dict, controls: dict) -> dict:
    """Combine one measured AI run with the current sidebar scenario."""
    return scenario_from_measured_run(
        measured,
        controls,
        cost_stress_multiplier=controls["cost_stress_multiplier"],
    )


def contribution_vs_cost_chart(
    scenario: dict, runtime_economics: dict | None = None
) -> go.Figure:
    labels = ["Recovered contribution", "AI inference cost"]
    values = [
        scenario["recovered_contribution_per_month"],
        scenario["ai_inference_cost_per_month"],
    ]
    if runtime_economics is not None:
        labels = [
            "Recovered contribution",
            "Azure runtime cost",
            "AI inference cost",
        ]
        values = [
            scenario["recovered_contribution_per_month"],
            runtime_economics["allocated_azure_runtime_cost_usd"],
            scenario["ai_inference_cost_per_month"],
        ]
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                text=[money(value) for value in values],
                textposition="auto",
            )
        ]
    )

    fig.update_layout(
        title=(
            "Monthly Modeled Contribution vs Technical Cost Boundaries"
            if runtime_economics is not None
            else "Monthly Contribution vs. AI Inference Cost"
        ),
        yaxis_title="USD / month",
        showlegend=False,
        height=390,
        margin=dict(l=20, r=20, t=55, b=20),
    )
    return fig


def conversion_sensitivity_chart(
    measured: dict,
    controls: dict,
    cost_snapshot: dict | None = None,
) -> go.Figure:
    """Vary only conversion while holding the measured AI run fixed."""
    conversion_rates = [index / 100 for index in range(0, 51)]

    scenarios = conversion_sensitivity(
        measured,
        controls,
        conversion_rates,
        cost_stress_multiplier=controls["cost_stress_multiplier"],
    )

    inference_multiples = [
        scenario["ai_value_multiple"] for scenario in scenarios
    ]

    selected_conversion_rate = controls["conversion_rate"]

    fig = go.Figure()
    runtime_multiples = None
    if cost_snapshot is not None:
        runtime_scenarios = [
            dashboard_views.scenario_runtime_economics(
                modeled_business_economics=scenario,
                cost_snapshot=cost_snapshot,
                workload_id=WORKLOAD_ID,
                modeled_days_per_month=controls["days_per_month"],
            )
            for scenario in scenarios
        ]
        if all(item is not None for item in runtime_scenarios):
            runtime_multiples = [
                item["modeled_azure_runtime_value_multiple"]
                for item in runtime_scenarios
            ]
            fig.add_trace(
                go.Scatter(
                    x=[rate * 100 for rate in conversion_rates],
                    y=runtime_multiples,
                    mode="lines+markers",
                    name="Azure Runtime Value Multiple",
                    hovertemplate=(
                        "Conversion: %{x:.0f}%<br>"
                        "Azure Runtime Value Multiple: %{y:.1f}x"
                        "<extra></extra>"
                    ),
                )
            )
    fig.add_trace(
        go.Scatter(
            x=[rate * 100 for rate in conversion_rates],
            y=inference_multiples,
            mode="lines+markers",
            name="AI Value Multiple - inference only",
            hovertemplate=(
                "Conversion: %{x:.0f}%<br>"
                "AI Value Multiple (inference only): %{y:.1f}x"
                "<extra></extra>"
            ),
        )
    )

    fig.add_hline(
        y=1.0,
        line_dash="dash",
        annotation_text="Break even (1.0x)",
        annotation_position="top left",
    )

    fig.add_vline(
        x=selected_conversion_rate * 100,
        line_dash="dot",
        annotation_text=f"Selected: {selected_conversion_rate:.0%}",
        annotation_position="top",
    )

    fig.update_layout(
        title=(
            "Sensitivity: Azure Runtime and AI Value Multiples vs. Conversion Rate"
            if runtime_multiples is not None
            else "Sensitivity: AI Value Multiple vs. Conversion Rate"
        ),
        xaxis_title="Conversion rate (%)",
        yaxis_title=(
            "Modeled value multiple"
            if runtime_multiples is not None else "AI Value Multiple"
        ),
        height=390,
        margin=dict(l=20, r=20, t=55, b=20),
    )
    return fig


def comparison_value_chart(
    label_a: str,
    scenario_a: dict,
    label_b: str,
    scenario_b: dict,
) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Bar(
                x=[label_a, label_b],
                y=[
                    scenario_a["ai_value_multiple"],
                    scenario_b["ai_value_multiple"],
                ],
                text=[
                    f"{scenario_a['ai_value_multiple']:.1f}x",
                    f"{scenario_b['ai_value_multiple']:.1f}x",
                ],
                textposition="auto",
            )
        ]
    )
    fig.add_hline(
        y=1.0,
        line_dash="dash",
        annotation_text="Break even",
        annotation_position="top left",
    )
    fig.update_layout(
        title="AI Value Multiple — Same Business Scenario",
        yaxis_title="Recovered contribution per $1 AI cost",
        showlegend=False,
        height=390,
    )
    return fig


def comparison_quality_cost_chart(
    label_a: str,
    run_a: dict,
    label_b: str,
    run_b: dict,
) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=[run_a["cost_per_task"], run_b["cost_per_task"]],
            y=[run_a["success_rate"] * 100, run_b["success_rate"] * 100],
            mode="markers+text",
            text=[label_a, label_b],
            textposition="top center",
            marker=dict(size=16),
            hovertemplate=(
                "Cost/interaction: $%{x:.6f}<br>"
                "Success rate: %{y:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title="Measured Quality vs. Cost",
        xaxis_title="Measured AI cost / interaction (USD)",
        yaxis_title="Behavior success rate (%)",
        height=390,
        showlegend=False,
    )
    return fig


def render_measured_performance(measured: dict) -> None:
    st.subheader("Measured AI Performance")
    st.caption(
        f"Latest evaluation run: `{measured['run_id']}`. "
        "These values are measured and are not editable."
    )

    cols = st.columns(4)
    cols[0].metric(
        "Behavior success rate",
        f"{measured['success_rate']:.1%}",
        border=True,
    )
    cols[1].metric(
        "Tokens / interaction",
        f"{measured['tokens_per_task']:,.0f}",
        border=True,
    )
    cols[2].metric(
        "Measured AI cost / interaction",
        money(measured["cost_per_task"], 6),
        border=True,
    )
    cols[3].metric(
        "Cost / successful resolution",
        money(measured["cost_per_success"], 6),
        border=True,
    )


def render_scenario_controls(latest: dict) -> dict:
    """Render shared scenario controls and return normalized values."""
    with st.sidebar:
        st.header("Scenario Controls")

        st.caption("Quick scenarios")
        preset_cols = st.columns(3)

        if preset_cols[0].button("Conservative", width='stretch'):
            apply_preset("Conservative")
            st.rerun()

        if preset_cols[1].button("Base", width='stretch'):
            apply_preset("Base Case")
            st.rerun()

        if preset_cols[2].button("Optimistic", width='stretch'):
            apply_preset("Optimistic")
            st.rerun()

        if st.button("Reset to latest run assumptions", width='stretch'):
            reset_to_latest(latest)
            st.rerun()

        st.divider()

        missed_contacts = st.slider(
            "Missed contacts / day",
            min_value=0,
            max_value=300,
            step=5,
            key="missed_contacts",
            help="Customer contacts the business currently cannot serve.",
        )

        ai_eligible_rate = st.slider(
            "AI-eligible contacts",
            min_value=0,
            max_value=100,
            step=5,
            format="%d%%",
            key="ai_eligible_pct",
            help="Share of missed contacts that the agent could reasonably handle.",
        ) / 100

        conversion_rate = st.slider(
            "Conversion after successful interaction",
            min_value=0,
            max_value=50,
            step=1,
            format="%d%%",
            key="conversion_pct",
            help=(
                "Assumed share of successfully served contacts that result "
                "in an order."
            ),
        ) / 100

        average_order_value = st.slider(
            "Average order value",
            min_value=1.0,
            max_value=40.0,
            step=0.50,
            format="$%.2f",
            key="average_order_value",
        )

        contribution_margin = st.slider(
            "Contribution margin",
            min_value=5,
            max_value=70,
            step=1,
            format="%d%%",
            key="contribution_margin_pct",
            help="Revenue remaining after direct variable costs.",
        ) / 100

        cost_stress_multiplier = st.slider(
            "AI cost stress multiplier",
            min_value=1.0,
            max_value=20.0,
            step=1.0,
            format="%.0fx",
            key="cost_stress_multiplier",
            help=(
                "Stress-test higher production inference cost without changing "
                "the measured baseline."
            ),
        )

        st.caption(
            f"Measured cost: {money(latest['cost_per_task'], 6)} / interaction"
        )
        st.caption(
            "Scenario cost for latest run: "
            f"{money(latest['cost_per_task'] * cost_stress_multiplier, 6)} "
            "/ interaction"
        )

    return {
        "missed_contacts_per_day": float(missed_contacts),
        "ai_eligible_rate": ai_eligible_rate,
        "conversion_rate": conversion_rate,
        "average_order_value_usd": average_order_value,
        "contribution_margin": contribution_margin,
        "days_per_month": int(latest["days_per_month"]),
        "cost_stress_multiplier": cost_stress_multiplier,
    }


def _snapshot_period_label(snapshot: dict) -> str:
    period = snapshot["cost_period"]
    start = date.fromisoformat(period["start"])
    end = date.fromisoformat(period["end"])
    return f"{start.strftime('%b')} {start.day}-{end.day}, {end.year}"


def load_available_cost_snapshots(
    directory: Path = COST_SNAPSHOTS_DIR,
) -> tuple[dict[str, tuple[Path, dict]], list[str]]:
    """Read validated, workload-compatible snapshots; never contact Azure."""
    snapshots = {}
    errors = []
    duplicate_ids = set()
    if not directory.exists():
        return snapshots, errors
    for path in sorted(directory.glob("*.json")):
        try:
            snapshot = load_cost_snapshot(path, workload_id=WORKLOAD_ID)
        except (OSError, ValueError) as error:
            errors.append(f"{path.name}: {error}")
            continue
        if snapshot["snapshot_id"] in snapshots:
            errors.append(
                f"{path.name}: duplicate snapshot_id {snapshot['snapshot_id']!r}"
            )
            snapshots.pop(snapshot["snapshot_id"], None)
            duplicate_ids.add(snapshot["snapshot_id"])
            continue
        if snapshot["snapshot_id"] in duplicate_ids:
            errors.append(
                f"{path.name}: duplicate snapshot_id {snapshot['snapshot_id']!r}"
            )
            continue
        snapshots[snapshot["snapshot_id"]] = (path, snapshot)
    return snapshots, errors


def render_cost_snapshot_selector() -> dict | None:
    snapshots, errors = load_available_cost_snapshots()
    with st.sidebar:
        st.divider()
        st.subheader("Azure system cost")
        selected_id = st.selectbox(
            "Cost snapshot",
            options=[None, *snapshots],
            format_func=lambda value: value or "No Azure cost snapshot",
        )
        for error in errors:
            st.warning(f"Snapshot unavailable: {error}")
        if selected_id is None:
            st.caption("System economics: NOT AVAILABLE")
            return None
        _, snapshot = snapshots[selected_id]
        st.caption(f"Period: {_snapshot_period_label(snapshot)}")
        st.caption(
            "Allocated Azure runtime cost: "
            f"{money(snapshot['allocated_azure_runtime_cost_usd'])}"
        )
        st.caption(
            f"Allocation status: {snapshot['allocation_status'].replace('_', ' ').upper()}"
        )
    return snapshot


def render_business_economics(
    latest: dict, controls: dict, cost_snapshot: dict | None = None
) -> None:
    render_measured_performance(latest)

    st.subheader("Demand-Recovery Funnel")

    scenario = calculate_scenario(latest, controls)
    runtime_economics = (
        dashboard_views.scenario_runtime_economics(
            modeled_business_economics=scenario,
            cost_snapshot=cost_snapshot,
            workload_id=WORKLOAD_ID,
            modeled_days_per_month=controls["days_per_month"],
        )
        if cost_snapshot is not None else None
    )

    cols = st.columns(4)
    cols[0].metric(
        "Missed contacts / day",
        f"{controls['missed_contacts_per_day']:,.0f}",
        border=True,
    )
    cols[1].metric(
        "AI-addressable / day",
        f"{scenario['addressable_contacts_per_day']:,.1f}",
        border=True,
    )
    cols[2].metric(
        "Successfully served / day",
        f"{scenario['successful_contacts_per_day']:,.1f}",
        border=True,
    )
    cols[3].metric(
        "Recovered orders / day",
        f"{scenario['recovered_orders_per_day']:,.1f}",
        border=True,
    )

    st.subheader("Estimated Economics")

    if runtime_economics is not None:
        st.markdown("#### SYSTEM ECONOMICS - broader Azure operating boundary")
        system_cols = st.columns(3)
        system_cols[0].metric(
            "Modeled Azure Runtime Value Multiple",
            f"{runtime_economics['modeled_azure_runtime_value_multiple']:,.1f}x",
            border=True,
            help="Primary system-economics multiple using the selected period-level cost snapshot.",
        )
        system_cols[1].metric(
            "Allocated Azure runtime cost / month",
            money(runtime_economics["allocated_azure_runtime_cost_usd"]),
            border=True,
        )
        system_cols[2].metric(
            "Contribution after Azure runtime",
            money(runtime_economics["modeled_contribution_after_azure_runtime_usd"]),
            border=True,
        )
        st.caption(
            "Includes allocated Azure Search, Foundry/model runtime, and observability. "
            "The selected snapshot is a fixed monthly cost baseline while scenario assumptions change."
        )
        st.markdown("#### MODEL ECONOMICS - inference-only lens")
        model_cols = st.columns(3)
        model_cols[0].metric(
            "Modeled recovered contribution / month",
            money(scenario["recovered_contribution_per_month"]),
            border=True,
        )
        model_cols[1].metric(
            "Projected inference cost / month",
            money(scenario["ai_inference_cost_per_month"]),
            border=True,
        )
        model_cols[2].metric(
            "Modeled AI Value Multiple - inference only",
            f"{scenario['ai_value_multiple']:,.1f}x",
            border=True,
            help="Secondary inference-efficiency metric; its denominator remains projected inference cost only.",
        )
        st.caption(
            f"Scenario analysis against {_snapshot_period_label(cost_snapshot)} "
            "observed/allocated monthly cost. This is not a per-run Azure cost."
        )
    else:
        cols = st.columns(4)
        cols[0].metric(
            "Recovered revenue / month",
            money(scenario["recovered_revenue_per_month"]),
            border=True,
        )
        cols[1].metric(
            "Recovered contribution / month",
            money(scenario["recovered_contribution_per_month"]),
            border=True,
        )
        cols[2].metric(
            "AI inference cost / month",
            money(scenario["ai_inference_cost_per_month"]),
            border=True,
        )
        cols[3].metric(
            "Modeled AI Value Multiple",
            f"{scenario['ai_value_multiple']:,.1f}x",
            border=True,
            help="Recovered contribution divided by AI inference cost.",
        )
        st.info("System economics: NOT AVAILABLE - no compatible Azure cost snapshot.")

    cols = st.columns(3)
    cols[0].metric(
        "Recovered orders / month",
        f"{scenario['recovered_orders_per_month']:,.1f}",
        border=True,
    )
    cols[1].metric(
        "Expected contribution / successful interaction",
        money(scenario["expected_contribution_per_success_usd"]),
        border=True,
    )
    cols[2].metric(
        "Break-even conversion rate",
        f"{scenario['break_even_conversion_rate']:.2%}",
        border=True,
    )

    left, right = st.columns(2)

    with left:
        st.plotly_chart(
            contribution_vs_cost_chart(scenario, runtime_economics),
            width="stretch",
        )

    with right:
        st.plotly_chart(
            conversion_sensitivity_chart(
                latest,
                controls,
                cost_snapshot if runtime_economics is not None else None,
            ),
            width="stretch",
        )

    st.subheader("Interpretation")

    multiple_to_interpret = (
        runtime_economics["modeled_azure_runtime_value_multiple"]
        if runtime_economics is not None else scenario["ai_value_multiple"]
    )
    multiple_name = (
        "Modeled Azure Runtime Value Multiple"
        if runtime_economics is not None else "Modeled AI Value Multiple"
    )
    if multiple_to_interpret >= 1:
        st.success(
            "Under the selected assumptions, modeled recovered contribution "
            f"exceeds the denominator for {multiple_name}."
        )
    else:
        st.warning(
            "Under the selected assumptions, modeled recovered contribution "
            f"does not cover the denominator for {multiple_name}."
        )

    st.markdown(
        """
**Optimization target:** economically valuable outcomes per dollar of inference,
not minimum token consumption.

**Measured:** token usage, inference cost, behavior success rate, cost per
successful resolution.

**Assumed:** missed demand, AI-eligible rate, conversion rate, average order
value, and contribution margin.

**Validate in a real pilot:** actual missed demand, incremental orders,
conversion lift, average order value, and contribution lift.
"""
    )


def run_label(record: dict, index: int) -> str:
    """Human-readable label without requiring agent metadata in old records."""
    agent_version = record.get("agent_version")
    model = record.get("model")

    extras = []
    if agent_version:
        extras.append(f"agent v{agent_version}")
    if model:
        extras.append(str(model))

    suffix = f" — {', '.join(extras)}" if extras else ""
    return f"{index + 1}. {record['run_id']}{suffix}"


def render_agent_comparison(runs: list[dict], controls: dict) -> None:
    st.subheader("Agent / Run Comparison")
    st.caption(
        "Compare two measured evaluation runs under exactly the same business "
        "assumptions. This isolates differences in quality and inference cost."
    )

    if len(runs) < 2:
        st.info(
            "At least two compatible business-economics runs are needed for "
            "comparison. Run `uv run scripts/run_evaluation.py` again after "
            "changing an agent, prompt, model, or configuration."
        )
        return

    labels = [run_label(record, index) for index, record in enumerate(runs)]

    selector_cols = st.columns(2)
    selected_a = selector_cols[0].selectbox(
        "Run A",
        options=range(len(runs)),
        index=max(0, len(runs) - 2),
        format_func=lambda index: labels[index],
    )
    selected_b = selector_cols[1].selectbox(
        "Run B",
        options=range(len(runs)),
        index=len(runs) - 1,
        format_func=lambda index: labels[index],
    )

    run_a = runs[selected_a]
    run_b = runs[selected_b]

    scenario_a = calculate_scenario(run_a, controls)
    scenario_b = calculate_scenario(run_b, controls)

    st.caption(
        "Both runs below use the current sidebar assumptions and the same AI "
        "cost stress multiplier."
    )

    table_data = {
        "Metric": [
            "Behavior success rate",
            "Tokens / interaction",
            "Measured cost / interaction",
            "Cost / successful resolution",
            "Modeled AI cost / month",
            "Recovered contribution / month",
            "AI Value Multiple",
            "Break-even conversion",
        ],
        "Run A": [
            f"{run_a['success_rate']:.1%}",
            f"{run_a['tokens_per_task']:,.0f}",
            money(run_a["cost_per_task"], 6),
            money(run_a["cost_per_success"], 6),
            money(scenario_a["ai_inference_cost_per_month"]),
            money(scenario_a["recovered_contribution_per_month"]),
            f"{scenario_a['ai_value_multiple']:.1f}x",
            f"{scenario_a['break_even_conversion_rate']:.2%}",
        ],
        "Run B": [
            f"{run_b['success_rate']:.1%}",
            f"{run_b['tokens_per_task']:,.0f}",
            money(run_b["cost_per_task"], 6),
            money(run_b["cost_per_success"], 6),
            money(scenario_b["ai_inference_cost_per_month"]),
            money(scenario_b["recovered_contribution_per_month"]),
            f"{scenario_b['ai_value_multiple']:.1f}x",
            f"{scenario_b['break_even_conversion_rate']:.2%}",
        ],
    }

    st.dataframe(
        table_data,
        hide_index=True,
        width='stretch',
    )

    charts = st.columns(2)

    with charts[0]:
        st.plotly_chart(
            comparison_value_chart(
                "Run A",
                scenario_a,
                "Run B",
                scenario_b,
            ),
            width="stretch",
        )

    with charts[1]:
        st.plotly_chart(
            comparison_quality_cost_chart(
                "Run A",
                run_a,
                "Run B",
                run_b,
            ),
            width="stretch",
        )

    token_delta = (
        (run_b["tokens_per_task"] - run_a["tokens_per_task"])
        / run_a["tokens_per_task"]
        if run_a["tokens_per_task"]
        else 0.0
    )
    cost_delta = (
        (run_b["cost_per_task"] - run_a["cost_per_task"])
        / run_a["cost_per_task"]
        if run_a["cost_per_task"]
        else 0.0
    )
    quality_delta_points = (
        run_b["success_rate"] - run_a["success_rate"]
    ) * 100
    value_delta = (
        (scenario_b["ai_value_multiple"] - scenario_a["ai_value_multiple"])
        / scenario_a["ai_value_multiple"]
        if scenario_a["ai_value_multiple"]
        else 0.0
    )

    st.markdown("#### What changed from Run A → Run B?")

    delta_cols = st.columns(4)
    delta_cols[0].metric(
        "Tokens / interaction",
        f"{run_b['tokens_per_task']:,.0f}",
        delta=f"{token_delta:+.1%}",
        border=True,
    )
    delta_cols[1].metric(
        "Measured cost / interaction",
        money(run_b["cost_per_task"], 6),
        delta=f"{cost_delta:+.1%}",
        border=True,
    )
    delta_cols[2].metric(
        "Behavior quality",
        f"{run_b['success_rate']:.1%}",
        delta=f"{quality_delta_points:+.1f} pp",
        border=True,
    )
    delta_cols[3].metric(
        "AI Value Multiple",
        f"{scenario_b['ai_value_multiple']:.1f}x",
        delta=f"{value_delta:+.1%}",
        border=True,
    )

    if scenario_b["ai_value_multiple"] > scenario_a["ai_value_multiple"]:
        st.success(
            "Under the same business assumptions, Run B produces the stronger "
            "modeled economics per dollar of AI inference."
        )
    elif scenario_b["ai_value_multiple"] < scenario_a["ai_value_multiple"]:
        st.info(
            "Under the same business assumptions, Run A produces the stronger "
            "modeled economics per dollar of AI inference."
        )
    else:
        st.info(
            "Under the same business assumptions, both runs have the same "
            "modeled AI Value Multiple."
        )

    st.markdown(
        """
**Why this comparison matters:** the cheapest or lowest-token run is not
automatically the best choice. A configuration that spends more tokens can
still be economically superior if the quality gain produces more successful,
valuable outcomes.
"""
    )


def main() -> None:
    st.set_page_config(
        page_title="Contoso Coffee Token Economics",
        page_icon="☕",
        layout="wide",
    )

    st.title("☕ Contoso Coffee — Token Economics")
    st.caption(
        "Demand recovery, not labor replacement: "
        "how much contribution can AI recover per dollar of inference?"
    )

    try:
        runs = history.load_business_runs()
    except (FileNotFoundError, RuntimeError, json.JSONDecodeError) as exc:
        st.error(str(exc))
        st.stop()

    latest = runs[-1]

    initialize_scenario_state(latest)
    controls = render_scenario_controls(latest)
    cost_snapshot = render_cost_snapshot_selector()

    business_tab, comparison_tab = st.tabs(
        ["Business Economics", "Agent / Run Comparison"]
    )

    with business_tab:
        render_business_economics(latest, controls, cost_snapshot)

    with comparison_tab:
        render_agent_comparison(runs, controls)


if __name__ == "__main__":
    main()