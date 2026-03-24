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
    "Forecasting",
    "Daily volume outlook, hourly workload shape, labor demand by shift, and congestion risk scoring."
)
eval_frame = artifacts.forecasting.evaluation
best_model = eval_frame.sort_values("rmse").iloc[0]
render_stat_cards(
    [
        ("Best Model", str(best_model["model"]), "Lowest RMSE on the holdout window."),
        ("MAE", f"{best_model['mae']:.2f}", "Average forecast error in trucks."),
        ("RMSE", f"{best_model['rmse']:.2f}", "Penalty-weighted error signal."),
        ("MAPE", f"{best_model['mape']:.1f}%", "Relative forecast error."),
    ]
)
left, right = st.columns([1.8, 1.2])
with left:
    line = px.line(
        artifacts.forecasting.daily_forecast,
        x="date",
        y=["forecast_inbound_truck_volume", "baseline_reference"],
        title="Daily Inbound Forecast",
        color_discrete_sequence=["#0b5c7a", "#f28f3b"],
    )
    line.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(line, use_container_width=True)
with right:
    risk = px.bar(
        artifacts.forecasting.congestion_risk_forecast.sort_values(
            "predicted_congestion_probability", ascending=False
        ).head(8),
        x="hour_of_day",
        y="predicted_congestion_probability",
        title="Top Congestion Risk Hours",
        color_discrete_sequence=["#12343b"],
    )
    risk.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(risk, use_container_width=True)

bottom_left, bottom_right = st.columns([1.2, 1.8])
with bottom_left:
    labor = px.bar(
        artifacts.forecasting.labor_demand_forecast,
        x="shift",
        y="recommended_workers",
        title="Labor Demand by Shift",
        color_discrete_sequence=["#f28f3b"],
    )
    labor.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(labor, use_container_width=True)
with bottom_right:
    st.subheader("Model Evaluation")
    st.dataframe(eval_frame, use_container_width=True, hide_index=True)

render_download(artifacts.forecasting.daily_forecast, "Download daily forecast", "daily_forecast.csv")
