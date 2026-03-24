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
    "Labor Planning",
    "Shift-level labor demand, available staffing, and the gap that drives queueing and overtime."
)
plan = artifacts.optimization.labor_plan.copy()
largest_gap = plan.sort_values("gap_workers", ascending=False).iloc[0]
render_stat_cards(
    [
        ("Largest Gap", f"{largest_gap['gap_workers']:.1f}", "Biggest worker shortfall across shifts."),
        ("Most Pressured Shift", str(largest_gap["shift"]), "Primary staffing concern right now."),
        ("Required Workers", f"{plan['required_workers'].sum():.0f}", "Aggregate requirement across shifts."),
        ("Available Workers", f"{plan['available_workers'].sum():.0f}", "Average available staffing across shifts."),
    ]
)
left, right = st.columns([1.3, 1.7])
with left:
    fig = px.bar(
        plan,
        x="shift",
        y=["required_workers", "available_workers"],
        barmode="group",
        title="Required vs Available",
        color_discrete_sequence=["#12343b", "#f28f3b"],
    )
    fig.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(fig, use_container_width=True)
with right:
    gap = px.bar(
        plan,
        x="shift",
        y="gap_workers",
        title="Labor Gap by Shift",
        color="gap_workers",
        color_continuous_scale=["#7a8b5a", "#f2c14e", "#f28f3b"],
    )
    gap.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(gap, use_container_width=True)

st.dataframe(plan, use_container_width=True, hide_index=True)
render_download(plan, "Download labor plan", "labor_plan.csv")
