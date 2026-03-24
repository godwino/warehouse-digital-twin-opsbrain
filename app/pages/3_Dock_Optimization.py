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

artifacts = run_mvp_pipeline(ScenarioConfig())
render_page_hero(
    "Dock Optimization",
    "Recommended dock assignments and labor posture intended to lower delay, congestion, and service-level risk."
)
summary = artifacts.optimization.summary.iloc[0]
render_stat_cards(
    [
        ("Objective", str(summary["objective"]).replace("_", " "), "Primary scheduling goal."),
        ("Optimized Trucks", f"{int(summary['trucks_optimized'])}", "Inbound trucks in current planning window."),
        ("Active Docks", f"{int(summary['active_docks'])}", "Usable door capacity for the schedule."),
        (
            "Delay Reduction",
            f"{int(summary['estimated_delay_reduction_minutes'])} min",
            "Estimated reduction versus naive scheduling.",
        ),
    ]
)
left, right = st.columns([1.1, 1.9])
with left:
    dock_counts = (
        artifacts.optimization.dock_assignments.groupby("recommended_dock_id")["truck_id"].count().reset_index()
    )
    fig = px.bar(
        dock_counts,
        x="recommended_dock_id",
        y="truck_id",
        title="Assigned Trucks by Dock",
        color_discrete_sequence=["#0b5c7a"],
    )
    fig.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Recommended Dock Assignments")
    st.dataframe(artifacts.optimization.dock_assignments, use_container_width=True, hide_index=True)

render_download(artifacts.optimization.dock_assignments, "Download dock plan", "dock_assignments.csv")
