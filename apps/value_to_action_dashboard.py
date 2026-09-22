"""Participant-facing Value-to-Action dashboard.

Run from the repository root:
    uv run streamlit run apps/value_to_action_dashboard.py

Read-only presentation layer over run evidence packages in ``runs/<run_id>/``.
It never calls the agent, Azure, Foundry, evaluators, or simulation generators,
and never recalculates economics or decision logic — all values come straight
from the stored ``summary.json`` / ``interactions.jsonl`` via pure helpers.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from foundry_prompt_agent import dashboard_views as views
from foundry_prompt_agent.run_reader import (
    RunPackageError,
    discover_run_ids,
    latest_run_id,
    load_run,
)

st.set_page_config(page_title="Contoso Coffee — Value-to-Action", layout="wide")


def _money(value) -> str:
    return f"${value:,.2f}" if isinstance(value, (int, float)) else "—"


def _pct(value) -> str:
    return f"{value:.1%}" if isinstance(value, (int, float)) else "—"


def main() -> None:
    st.title("Contoso Coffee — Value-to-Action")
    st.caption("MEASURE → PROVE → VALUE → TEST → DECIDE → ACT")

    run_ids = discover_run_ids()
    if not run_ids:
        st.warning(
            "No run evidence packages found under runs/. "
            "Generate one with scripts/run_evaluation.py or run_simulation.py."
        )
        return

    default_id = latest_run_id()
    selected = st.sidebar.selectbox(
        "Run package",
        options=list(reversed(run_ids)),
        index=0 if default_id is None else list(reversed(run_ids)).index(default_id),
    )

    try:
        run = load_run(selected)
    except RunPackageError as error:
        st.error(f"Could not load run {selected!r}: {error}")
        return

    summary = run["summary"]
    interactions = run["interactions"]
    meta = views.run_metadata(summary, interactions)
    simulation = views.is_simulation(summary)

    with st.sidebar:
        st.subheader("Run metadata")
        st.write({k: v for k, v in meta.items() if v is not None})

    _render_header(meta, simulation)
    _render_journey(summary)
    _render_measure(summary, interactions)
    _render_prove(summary, simulation)
    _render_value(summary)
    _render_test(summary)
    _render_decide(summary)
    _render_act(summary)
    _render_explorer(interactions)


def _render_header(meta: dict, simulation: bool) -> None:
    columns = st.columns(3)
    columns[0].metric("Run ID", meta["run_id"] or "—")
    columns[1].metric("Run mode", (meta["run_mode"] or "—").upper())
    columns[2].metric("Evidence mode", (meta["evidence_mode"] or "—").upper())

    if simulation:
        st.warning(
            "**SIMULATION / SYNTHETIC EVIDENCE** — Synthetic customer workload "
            "+ real AI execution/evaluation + synthetic business outcomes. "
            "This is not production business evidence."
        )
    else:
        st.info(
            "**REGRESSION EVIDENCE** — Real AI execution/evaluation over the "
            "fixed regression suite. No downstream business evidence."
        )


def _render_journey(summary: dict) -> None:
    st.subheader("Journey")
    states = views.journey_states(summary)
    columns = st.columns(len(views.JOURNEY_STAGES))
    for column, stage in zip(columns, views.JOURNEY_STAGES):
        column.metric(stage, states[stage])


def _render_measure(summary: dict, interactions: list[dict]) -> None:
    st.subheader("MEASURE")
    metrics = views.measure_metrics(summary, interactions)

    row1 = st.columns(3)
    row1[0].metric("Attempted interactions", metrics["attempted_interactions"])
    row1[1].metric("Accepted interactions", metrics["accepted_interactions"])
    row1[2].metric("Acceptance rate", _pct(metrics["acceptance_rate"]))

    row2 = st.columns(3)
    row2[0].metric(
        "Known direct execution cost",
        _money(metrics["known_direct_execution_cost_usd"]),
    )
    row2[1].metric(
        "Known direct cost / Accepted Work",
        _money(metrics["known_direct_cost_per_accepted_work_usd"]),
    )
    row2[2].metric("Measured tool calls", metrics["measured_tool_calls"] or "—")

    st.caption(
        f"Cost completeness: **{(metrics['cost_completeness'] or 'unknown').upper()}**. "
        "This is the *known direct* execution cost (model inference), not the "
        "Full Execution Cost or Total Relevant Customer Cost — those remain "
        "incomplete."
    )


def _render_prove(summary: dict, simulation: bool) -> None:
    st.subheader("PROVE")
    experiment = views.prove_view(summary)

    if experiment is None:
        st.info(
            "Downstream business and counterfactual evidence are **Unknown** "
            "for this run. No treatment/control experiment is present."
        )
        return

    row = st.columns(4)
    row[0].metric("Eligible", experiment.get("eligible_interactions", "—"))
    row[1].metric("Treatment", experiment.get("treatment_count", "—"))
    row[2].metric("Control", experiment.get("control_count", "—"))
    row[3].metric(
        "Simulated lift (pp)",
        f"{experiment.get('simulated_conversion_lift_pp', 0):.1f}",
    )

    treatment_conv = experiment.get("treatment_conversion", 0.0)
    control_conv = experiment.get("control_conversion", 0.0)
    figure = go.Figure(
        data=[
            go.Bar(
                x=["Treatment (SIMULATED)", "Control (SIMULATED)"],
                y=[treatment_conv, control_conv],
                text=[_pct(treatment_conv), _pct(control_conv)],
                textposition="auto",
            )
        ]
    )
    figure.update_layout(
        title="SIMULATED conversion: Treatment vs Control",
        yaxis_title="SIMULATED conversion rate",
        showlegend=False,
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption("Evidence: **SYNTHETIC SIMULATION** — this is a simulated lift, not realized or production lift.")


def _render_value(summary: dict) -> None:
    st.subheader("VALUE")
    value = views.value_view(summary)

    st.markdown("**A. Modeled scenario economics (MODELED)**")
    modeled = value["modeled"]
    columns = st.columns(3)
    columns[0].metric(
        "Modeled recovered contribution", _money(modeled["recovered_contribution_usd"])
    )
    multiple = modeled["ai_value_multiple"]
    columns[1].metric(
        "Modeled AI Value Multiple",
        f"{multiple:,.1f}x" if isinstance(multiple, (int, float)) else "—",
    )
    columns[2].metric(
        "Cost completeness", (modeled["cost_completeness"] or "—").upper()
    )

    synthetic = value["synthetic"]
    if synthetic is not None:
        st.markdown("**B. Synthetic economics (SIMULATED)**")
        columns = st.columns(3)
        columns[0].metric(
            "Simulated incremental conversion",
            _pct(synthetic.get("simulated_incremental_conversion_rate")),
        )
        columns[1].metric(
            "Simulated incremental orders (sample)",
            f"{synthetic.get('simulated_incremental_orders_for_observed_sample', 0):.2f}",
        )
        columns[2].metric(
            "Synthetic avg order value",
            _money(synthetic.get("average_order_value_usd")),
        )
        columns = st.columns(2)
        columns[0].metric(
            "Simulated incremental revenue",
            _money(synthetic.get("simulated_incremental_revenue_usd")),
        )
        columns[1].metric(
            "Simulated incremental contribution",
            _money(synthetic.get("simulated_incremental_contribution_usd")),
        )
        st.caption("Every value above is **SIMULATED**, not production-established.")

    st.markdown("**C. Decision-grade economics**")
    decision = value["decision_grade"]
    net = decision["customer_net_economic_value_usd"]
    incremental = decision["incremental_net_economic_value_usd"]
    columns = st.columns(2)
    columns[0].metric(
        "Customer Net Economic Value",
        _money(net) if net is not None else "UNKNOWN / NOT ESTABLISHED",
    )
    columns[1].metric(
        "Incremental Net Economic Value",
        _money(incremental) if incremental is not None else "NOT ESTABLISHED",
    )


def _render_test(summary: dict) -> None:
    st.subheader("TEST")
    st.table(views.test_evidence_rows(summary))

    claims = views.assessment_claims(summary)
    labels = {
        "established": "Established claims",
        "simulated": "Simulated claims",
        "modeled": "Modeled claims",
        "unknown": "Unknown / real-world gaps",
    }
    for key, label in labels.items():
        items = claims[key]
        if not items:
            continue
        with st.expander(f"{label} ({len(items)})"):
            for item in items:
                st.markdown(f"- {item}")


def _render_decide(summary: dict) -> None:
    st.subheader("DECIDE")
    rows = views.decide_gate_rows(summary)
    if rows:
        st.table(rows)
    else:
        st.info("No decision gate record available for this run.")

    actions = views.decide_actions(summary)
    columns = st.columns(2)
    columns[0].markdown("**Eligible actions**")
    columns[0].write(actions["eligible"] or "—")
    columns[1].markdown("**Ineligible actions**")
    columns[1].write(actions["ineligible"] or "—")

    if not actions["scale_eligible"]:
        st.warning("SCALE is currently **ineligible**.")


def _render_act(summary: dict) -> None:
    st.subheader("ACT")
    act = views.act_view(summary)

    st.metric("Selected action", act["selected_action"])
    st.markdown(f"**Primary decision deficit:** {act['primary_decision_deficit']}")
    if act["action_rationale"]:
        st.markdown(f"**Rationale:** {act['action_rationale']}")

    columns = st.columns(2)
    with columns[0]:
        st.markdown("**Required work**")
        for item in act["required_work"]:
            st.markdown(f"- {item}")
    with columns[1]:
        st.markdown("**Required evidence**")
        for item in act["required_evidence"]:
            st.markdown(f"- {item}")

    if act["resource_request"]:
        st.caption(f"Resource request: {act['resource_request']}")
    if act["reassessment_trigger"]:
        st.caption(f"Reassessment trigger: {act['reassessment_trigger']}")


def _render_explorer(interactions: list[dict]) -> None:
    with st.expander("Interaction Explorer"):
        rows = views.interaction_table_rows(interactions)
        categories = sorted({r["category"] for r in rows if r["category"]})
        assignments = sorted({r["assignment"] for r in rows if r["assignment"]})

        columns = st.columns(2)
        category_filter = columns[0].multiselect("Category", categories)
        assignment_filter = columns[1].multiselect("Assignment", assignments)

        filtered = [
            row
            for row in rows
            if (not category_filter or row["category"] in category_filter)
            and (not assignment_filter or row["assignment"] in assignment_filter)
        ]
        st.dataframe(filtered, use_container_width=True)
        st.caption(
            "For simulation runs, control rows are shadow executions "
            "(exposure = ai_not_exposed_shadow_execution_only)."
        )


if __name__ == "__main__":
    main()
