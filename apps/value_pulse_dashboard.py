"""Compact, read-only AI Value Pulse dashboard.

Run from the repository root:
    uv run streamlit run apps/value_pulse_dashboard.py

This dashboard composes stored run evidence and existing presentation helpers.
It does not call Azure, Foundry, evaluators, or simulation generators.
"""

from __future__ import annotations

import streamlit as st

from foundry_prompt_agent.dashboard_views import build_value_pulse_view
from foundry_prompt_agent.run_reader import (
    RunPackageError,
    discover_run_ids,
    latest_run_id,
    load_run,
)

st.set_page_config(page_title="AI Value Pulse", layout="wide")


def _money(value, digits: int = 2) -> str:
    return (
        f"${value:,.{digits}f}"
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else "Not established"
    )


def _percent(value) -> str:
    return f"{value:.1%}" if isinstance(value, (int, float)) else "Not established"


def _metric(value, unit: str | None = None) -> str:
    if value is None:
        return "Not available"
    if unit == "USD":
        return _money(value)
    if unit == "percentage points":
        return f"{value:.1f} pp"
    if unit == "orders":
        return f"{value:,.0f}" if value == int(value) else f"{value:,.2f}"
    return str(value)


def main() -> None:
    st.title("AI Value Pulse")
    st.caption("Work → Measure → Outcome → Value → Action")

    run_ids = discover_run_ids()
    if not run_ids:
        st.info(
            "No run evidence packages found under runs/. "
            "Create a run package to view its evidence here."
        )
        return

    choices = list(reversed(run_ids))
    latest = latest_run_id()
    selected = st.sidebar.selectbox(
        "Run",
        options=choices,
        index=choices.index(latest) if latest in choices else 0,
    )
    try:
        run = load_run(selected)
    except RunPackageError as error:
        st.error(f"Could not load run {selected!r}: {error}")
        return

    pulse = build_value_pulse_view(run["summary"], run["interactions"])
    _render_context(pulse["context"])
    _render_stages(pulse)
    st.caption(
        "Need more detail? Token-to-Value dashboard: economics and scenarios. "
        "Value-to-Action dashboard: evidence and decision analysis."
    )


def _render_context(context: dict) -> None:
    columns = st.columns(4)
    columns[0].caption("WORKLOAD")
    columns[0].write(context["workload"])
    columns[1].caption("RUN / PERIOD")
    columns[1].write(f"{context['run_id']} · {context['period']}")
    columns[2].caption("EVIDENCE")
    columns[2].write(context["evidence_status"])
    columns[3].caption("CUSTOMER ECONOMICS")
    columns[3].write(context["customer_economics_status"])


def _render_stages(pulse: dict) -> None:
    columns = st.columns(5)
    work = pulse["work"]
    measure = pulse["measure"]
    outcome = pulse["outcome"]
    value = pulse["value"]
    action = pulse["action"]

    with columns[0].container(border=True):
        st.markdown("### WORK")
        st.markdown("**Objective**")
        st.write(work["objective"])
        st.markdown("**Accepted Work**")
        st.caption(work["accepted_work_definition"])

    with columns[1].container(border=True):
        st.markdown("### MEASURE")
        st.metric(
            "Accepted Work",
            (
                f"{measure['accepted_work_count']:,}"
                if measure["accepted_work_count"] is not None
                else "Not available"
            ),
        )
        st.metric("Accepted Work rate", _percent(measure["accepted_work_rate"]))
        system_cost = measure["system_cost_usd"]
        st.metric(
            "Azure runtime cost",
            _money(system_cost),
            help=(
                f"Period: {measure['system_cost_period']}; "
                f"evidence: {measure['system_cost_evidence']}."
            ),
        )
        st.caption(
            "Run inference cost / Accepted Work: "
            f"{_money(measure['cost_per_accepted_work_usd'], digits=6)}"
        )

    with columns[2].container(border=True):
        st.markdown("### OUTCOME")
        st.markdown(f"**{outcome['evidence_type']}**")
        st.metric(
            outcome["primary_metric_label"],
            _metric(
                outcome["primary_metric_value"],
                outcome["primary_metric_unit"],
            ),
        )
        st.caption(
            f"{outcome['magnitude_label']}: "
            f"{_metric(outcome['magnitude_value'], outcome['magnitude_unit'])}"
        )
        st.caption(f"Production outcome: {outcome['production_status']}")

    with columns[3].container(border=True):
        st.markdown("### VALUE")
        st.markdown(f"**{value['value_evidence_type']}**")
        st.metric(
            value["economic_value_label"],
            _money(value["economic_value_usd"]),
        )
        multiple = value["value_multiple"]
        multiple_text = (
            f"{multiple:,.1f}x"
            if isinstance(multiple, (int, float))
            else "Not established"
        )
        st.metric(value["value_multiple_label"], multiple_text)
        st.caption(f"Evidence confidence: {value['evidence_confidence']}")
        st.caption(
            f"Customer economics: {value['customer_economics_status']}"
        )

    with columns[4].container(border=True):
        st.markdown("### ACTION")
        st.markdown(f"**{action['selected_action']}**")
        st.caption(action["rationale"] or "No rationale recorded.")
        st.markdown("**Next**")
        st.write(action["next_step"] or "No next step recorded.")


if __name__ == "__main__":
    main()
