from pathlib import Path
import sys

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.ui import render_download, render_page_hero, render_stat_cards
from src.config.settings import ScenarioConfig
from src.utils.demo import run_mvp_pipeline

st.set_page_config(layout="wide")
artifacts = run_mvp_pipeline(ScenarioConfig())

render_page_hero(
    "Executive Overview",
    "A concise operating readout across service level, congestion, throughput, and action priority."
)
kpi_map = {row["kpi"]: row["value"] for _, row in artifacts.simulation.kpis.iterrows()}
render_stat_cards(
    [
        ("Service Level", f"{kpi_map['service_level_attainment']:.1%}", "Simulated attainment in current flow."),
        ("Wait Time", f"{kpi_map['average_truck_wait_time']:.1f} min", "Average inbound queue delay."),
        ("Labor Utilization", f"{kpi_map['labor_utilization']:.0%}", "Pressure on shift staffing."),
        ("Cost Estimate", f"${kpi_map['cost_estimate']:,.0f}", "Modeled operating cost proxy."),
    ]
)

left, right = st.columns([1.7, 1.3])
with left:
    st.subheader("Recommendation Priority")
    fig = px.bar(
        artifacts.recommendations.head(6),
        x="severity",
        y="recommendation",
        orientation="h",
        color="affected_kpi",
        color_discrete_sequence=["#0b5c7a", "#f28f3b", "#7a8b5a"],
    )
    fig.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Simulation KPI Table")
    st.dataframe(artifacts.simulation.kpis, use_container_width=True, hide_index=True)

render_download(artifacts.recommendations, "Download recommendations", "executive_recommendations.csv")
