from __future__ import annotations

from pathlib import Path
import sys

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.config.settings import ScenarioConfig
from src.utils.demo import load_run_history, run_mvp_pipeline


st.set_page_config(
    page_title="HVDC OpsBrain",
    page_icon="HV",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(255,184,77,0.18), transparent 24%),
                radial-gradient(circle at top left, rgba(11,92,122,0.20), transparent 30%),
                linear-gradient(180deg, #f7f5ef 0%, #eef2f3 100%);
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        .hero-card {
            padding: 1.5rem 1.6rem;
            border-radius: 22px;
            color: #f7f5ef;
            background: linear-gradient(135deg, #12343b 0%, #0b5c7a 48%, #f28f3b 100%);
            box-shadow: 0 18px 45px rgba(18, 52, 59, 0.18);
            margin-bottom: 1rem;
        }
        .hero-title {
            font-size: 2.2rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 0.35rem;
        }
        .hero-subtitle {
            max-width: 62rem;
            opacity: 0.92;
            font-size: 1rem;
        }
        .section-chip {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            margin-right: 0.4rem;
            margin-top: 0.45rem;
            font-size: 0.82rem;
            color: #12343b;
            background: rgba(255,255,255,0.82);
        }
        .insight-card {
            background: rgba(255,255,255,0.82);
            border: 1px solid rgba(18,52,59,0.08);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            min-height: 140px;
        }
        .insight-label {
            color: #5a6a70;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .insight-value {
            color: #12343b;
            font-size: 1.7rem;
            font-weight: 700;
            margin: 0.15rem 0 0.3rem 0;
        }
        .insight-text {
            color: #355159;
            font-size: 0.92rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_demo(scenario_dict: dict) -> object:
    scenario = ScenarioConfig(**scenario_dict)
    return run_mvp_pipeline(scenario)


@st.cache_data(show_spinner=False, ttl=30)
def load_history() -> object:
    return load_run_history(limit=8)


def render_overview(artifacts: object, scenario: dict) -> None:
    inject_styles()
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">HVDC OpsBrain</div>
            <div class="hero-subtitle">
                Digital twin, forecasting, optimization, and operational recommendations for warehouse inbound flow.
                Use the controls on the left to stress-test the operation before queues, overtime, and breaches compound.
            </div>
            <div>
                <span class="section-chip">Forecast workload</span>
                <span class="section-chip">Optimize docks</span>
                <span class="section-chip">Simulate bottlenecks</span>
                <span class="section-chip">Recommend actions</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary_col, scenario_col = st.columns([2.6, 1.4])
    with summary_col:
        st.markdown("### Executive Pulse")
        st.write(
            "This view combines the forecast, the optimization plan, and the simulated flow outcome into a single operating readout."
        )
    with scenario_col:
        st.markdown("### Scenario")
        st.write(
            f"`{scenario['name']}` with `{scenario['inbound_volume_multiplier']:.2f}x` inbound volume, "
            f"`{scenario['labor_availability_ratio']:.2f}x` labor, and `{scenario['active_dock_ratio']:.2f}x` dock capacity."
        )

    kpis = artifacts.simulation.kpis
    kpi_map = {row["kpi"]: row["value"] for _, row in kpis.iterrows()}
    insight_cols = st.columns(4)
    cards = [
        (
            "Service Level",
            f"{kpi_map['service_level_attainment']:.1%}",
            "Simulated attainment after queueing and resource contention.",
        ),
        (
            "Avg Truck Wait",
            f"{kpi_map['average_truck_wait_time']:.1f} min",
            "Primary signal for dock-side congestion and schedule spillover.",
        ),
        (
            "Dock Utilization",
            f"{kpi_map['dock_utilization']:.0%}",
            "High values indicate stronger asset use but elevated queue risk.",
        ),
        (
            "Throughput",
            f"{int(kpi_map['throughput'])} trucks",
            "Processed volume in the modeled simulation window.",
        ),
    ]
    for col, (label, value, text) in zip(insight_cols, cards):
        col.markdown(
            f"""
            <div class="insight-card">
                <div class="insight-label">{label}</div>
                <div class="insight-value">{value}</div>
                <div class="insight-text">{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    daily = artifacts.forecasting.daily_forecast
    bottlenecks = artifacts.bottlenecks.head(6).copy()
    recs = artifacts.recommendations.head(5).copy()
    plan = artifacts.optimization.labor_plan.copy()

    left, right = st.columns([1.8, 1.2])
    with left:
        forecast_fig = go.Figure()
        forecast_fig.add_trace(
            go.Scatter(
                x=daily["date"],
                y=daily["forecast_inbound_truck_volume"],
                mode="lines+markers",
                name="Forecast",
                line=dict(color="#0b5c7a", width=3),
            )
        )
        forecast_fig.add_trace(
            go.Scatter(
                x=daily["date"],
                y=daily["baseline_reference"],
                mode="lines",
                name="Baseline",
                line=dict(color="#f28f3b", width=2, dash="dash"),
            )
        )
        forecast_fig.update_layout(
            title="Inbound Volume Outlook",
            paper_bgcolor="rgba(255,255,255,0.0)",
            plot_bgcolor="rgba(255,255,255,0.72)",
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(forecast_fig, use_container_width=True)
    with right:
        heat = px.bar(
            bottlenecks,
            x="severity",
            y="area",
            color="source",
            orientation="h",
            title="Bottleneck Pressure",
            color_discrete_sequence=["#0b5c7a", "#f28f3b", "#7a8b5a"],
        )
        heat.update_layout(
            paper_bgcolor="rgba(255,255,255,0.0)",
            plot_bgcolor="rgba(255,255,255,0.72)",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(heat, use_container_width=True)

    lower_left, lower_right = st.columns([1.3, 1.7])
    with lower_left:
        st.markdown("### Labor Posture")
        labor_fig = px.bar(
            plan,
            x="shift",
            y=["required_workers", "available_workers"],
            barmode="group",
            color_discrete_sequence=["#12343b", "#f28f3b"],
        )
        labor_fig.update_layout(
            paper_bgcolor="rgba(255,255,255,0.0)",
            plot_bgcolor="rgba(255,255,255,0.72)",
            margin=dict(l=10, r=10, t=10, b=10),
            legend_title_text="",
        )
        st.plotly_chart(labor_fig, use_container_width=True)
    with lower_right:
        st.markdown("### Top Recommendations")
        st.dataframe(
            recs[["recommendation", "expected_impact", "confidence", "affected_kpi"]],
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Download Current Recommendation Set"):
        st.download_button(
            "Download recommendations CSV",
            recs.to_csv(index=False).encode("utf-8"),
            file_name="opsbrain_recommendations.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download bottlenecks CSV",
            bottlenecks.to_csv(index=False).encode("utf-8"),
            file_name="opsbrain_bottlenecks.csv",
            mime="text/csv",
        )

    history = load_history()
    st.markdown("### Recent Scenario Runs")
    if len(history) == 0:
        st.write("No persisted run history available yet.")
    else:
        history_view = history[
            [
                "created_at",
                "scenario_name",
                "service_level_attainment",
                "average_truck_wait_time",
                "average_total_cycle_time",
                "throughput",
                "top_recommendation",
            ]
        ].copy()
        history_view["created_at"] = history_view["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(history_view, use_container_width=True, hide_index=True)


def main() -> None:
    st.sidebar.header("Scenario Lab")
    scenario_name = st.sidebar.selectbox(
        "Scenario",
        [
            "normal_operations",
            "peak_season",
            "labor_shortage",
            "dock_outage",
            "surge_inbound_day",
            "fragile_load_mix_increase",
        ],
    )
    inbound_volume_pct = st.sidebar.slider("Inbound volume %", 70, 180, 100, step=5)
    available_workers_pct = st.sidebar.slider("Available workers %", 50, 120, 100, step=5)
    active_docks = st.sidebar.slider("Active docks %", 50, 100, 100, step=5)
    fragile_mix = st.sidebar.slider("Fragile mix delta", 0.0, 0.4, 0.0, step=0.05)
    priority_mix = st.sidebar.slider("Priority mix delta", 0.0, 0.2, 0.0, step=0.02)
    operating_hours = st.sidebar.slider("Operating hours", 8, 24, 18, step=1)

    scenario = {
        "name": scenario_name,
        "horizon_days": 90,
        "random_seed": 42,
        "inbound_volume_multiplier": inbound_volume_pct / 100,
        "labor_availability_ratio": available_workers_pct / 100,
        "active_dock_ratio": active_docks / 100,
        "fragile_mix_delta": fragile_mix,
        "priority_mix_delta": priority_mix,
        "operating_hours": operating_hours,
    }
    artifacts = load_demo(scenario)

    render_overview(artifacts, scenario)
    st.info("Use the multipage navigation in the sidebar to explore the detailed modules.")


if __name__ == "__main__":
    main()
