from pathlib import Path
import sys

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.ui import render_download, render_page_hero, render_stat_cards
from src.utils.demo import compare_named_scenarios

render_page_hero(
    "Scenario Comparison",
    "Compare baseline and stressed operating cases side by side with KPI deltas, stage pressure shifts, and recommendation changes."
)

scenario_names = [
    "normal_operations",
    "peak_season",
    "labor_shortage",
    "dock_outage",
    "surge_inbound_day",
    "fragile_load_mix_increase",
]

left_selector, right_selector = st.columns(2)
with left_selector:
    baseline_name = st.selectbox("Baseline scenario", scenario_names, index=0)
with right_selector:
    comparison_name = st.selectbox("Comparison scenario", scenario_names, index=2)

comparison = compare_named_scenarios(baseline_name, comparison_name)
largest_kpi_shift = comparison.kpi_delta.iloc[comparison.kpi_delta["delta"].abs().idxmax()]
largest_stage_shift = comparison.stage_delta.iloc[0]

render_stat_cards(
    [
        ("Baseline", comparison.baseline_name, "Reference operating condition."),
        ("Comparison", comparison.comparison_name, "Scenario being stress-tested."),
        ("Largest KPI Shift", str(largest_kpi_shift["kpi"]), "Most changed simulated KPI."),
        ("Largest Stage Shift", str(largest_stage_shift["stage"]), "Stage with the biggest bottleneck movement."),
    ]
)

kpi_left, kpi_right = st.columns([1.7, 1.3])
with kpi_left:
    kpi_fig = px.bar(
        comparison.kpi_delta,
        x="kpi",
        y="delta",
        color="delta",
        title="KPI Delta: Comparison Minus Baseline",
        color_continuous_scale=["#7a8b5a", "#f2c14e", "#f28f3b"],
    )
    kpi_fig.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(kpi_fig, use_container_width=True)
with kpi_right:
    st.subheader("KPI Delta Table")
    st.dataframe(comparison.kpi_delta, use_container_width=True, hide_index=True)

stage_left, stage_right = st.columns([1.5, 1.5])
with stage_left:
    stage_fig = px.bar(
        comparison.stage_delta,
        x="stage",
        y="bottleneck_delta",
        color="bottleneck_delta",
        title="Bottleneck Frequency Delta",
        color_continuous_scale=["#7a8b5a", "#f2c14e", "#f28f3b"],
    )
    stage_fig.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(stage_fig, use_container_width=True)
with stage_right:
    cycle_compare = comparison.kpi_delta[
        comparison.kpi_delta["kpi"].isin(["average_truck_wait_time", "average_total_cycle_time", "service_level_attainment"])
    ]
    cycle_fig = px.bar(
        cycle_compare.melt(id_vars="kpi", value_vars=["baseline_value", "comparison_value"]),
        x="kpi",
        y="value",
        color="variable",
        barmode="group",
        title="Before vs After",
        color_discrete_sequence=["#12343b", "#f28f3b"],
    )
    cycle_fig.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(cycle_fig, use_container_width=True)

st.subheader("Recommendation Changes")
st.dataframe(comparison.recommendation_delta, use_container_width=True, hide_index=True)
render_download(comparison.kpi_delta, "Download KPI comparison", "scenario_kpi_comparison.csv")
