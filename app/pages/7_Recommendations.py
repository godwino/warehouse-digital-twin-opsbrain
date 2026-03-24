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
    "Recommendations",
    "Action-oriented operating guidance with impact framing, confidence, and affected KPIs."
)
recs = artifacts.recommendations.copy()
top = recs.iloc[0]
render_stat_cards(
    [
        ("Top Action", str(top["affected_kpi"]).replace("_", " "), "Primary KPI targeted by the lead recommendation."),
        ("Confidence", f"{top['confidence']:.0%}", "Confidence score for the top action."),
        ("Severity", f"{top['severity']:.2f}", "Urgency level attached to the action."),
        ("Actions", f"{len(recs)}", "Distinct recommended moves."),
    ]
)
left, right = st.columns([1.2, 1.8])
with left:
    fig = px.bar(
        recs.head(8),
        x="severity",
        y="affected_kpi",
        color="confidence",
        title="Recommendation Severity by KPI",
        color_continuous_scale=["#7a8b5a", "#f2c14e", "#f28f3b"],
    )
    fig.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.dataframe(recs, use_container_width=True, hide_index=True)

render_download(recs, "Download recommendations", "recommendations.csv")
