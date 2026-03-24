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
    "Bottleneck Analysis",
    "Cross-signal bottleneck view combining simulation friction, congestion forecasts, and labor gap pressure."
)
bottlenecks = artifacts.bottlenecks.copy()
top = bottlenecks.iloc[0]
render_stat_cards(
    [
        ("Top Constraint", str(top["area"]), "Most severe current hotspot."),
        ("Severity", f"{top['severity']:.2f}", "Highest stress level across signals."),
        ("Signal Source", str(top["source"]), "Where the hotspot is being detected."),
        ("Top Metric", f"{top['metric']:.1f}", "Associated KPI behind the alert."),
    ]
)
left, right = st.columns([1.5, 1.5])
with left:
    fig = px.bar(
        bottlenecks.head(10),
        x="severity",
        y="area",
        color="source",
        orientation="h",
        color_discrete_sequence=["#0b5c7a", "#f28f3b", "#7a8b5a"],
    )
    fig.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(fig, use_container_width=True)
with right:
    source_mix = bottlenecks.groupby("source").size().reset_index(name="count")
    pie = px.pie(source_mix, names="source", values="count", title="Hotspot Source Mix")
    pie.update_layout(paper_bgcolor="rgba(255,255,255,0)")
    st.plotly_chart(pie, use_container_width=True)

st.dataframe(bottlenecks, use_container_width=True, hide_index=True)
render_download(bottlenecks, "Download bottlenecks", "bottlenecks.csv")
