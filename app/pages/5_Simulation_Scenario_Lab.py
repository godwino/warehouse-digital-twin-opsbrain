from pathlib import Path
import sys

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.ui import render_download, render_page_hero, render_stat_cards
from src.config.settings import ScenarioConfig, build_named_scenario
from src.utils.demo import compare_named_scenarios, run_mvp_pipeline

render_page_hero(
    "Simulation / Scenario Lab",
    "Stress-test inbound flow by adjusting volume, staffing, dock capacity, and fragility mix, then inspect queue and throughput outcomes."
)
comparison_enabled = st.toggle("Compare against baseline scenario", value=True)
scenario = ScenarioConfig(
    inbound_volume_multiplier=st.slider("Inbound volume multiplier", 0.7, 1.8, 1.0, step=0.05),
    labor_availability_ratio=st.slider("Labor availability ratio", 0.5, 1.2, 1.0, step=0.05),
    active_dock_ratio=st.slider("Active dock ratio", 0.5, 1.0, 1.0, step=0.05),
    fragile_mix_delta=st.slider("Fragile mix delta", 0.0, 0.4, 0.0, step=0.05),
    operating_hours=st.slider("Operating hours", 8, 24, 18),
)
artifacts = run_mvp_pipeline(scenario)
kpi_map = {row["kpi"]: row["value"] for _, row in artifacts.simulation.kpis.iterrows()}
render_stat_cards(
    [
        ("Avg Wait", f"{kpi_map['average_truck_wait_time']:.1f} min", "Queueing result under this scenario."),
        ("Avg Unload", f"{kpi_map['average_unload_time']:.1f} min", "Dock processing time in simulation."),
        ("Service Level", f"{kpi_map['service_level_attainment']:.1%}", "Attainment after modeled contention."),
        ("Throughput", f"{int(kpi_map['throughput'])}", "Processed truck count in run."),
    ]
)
left, right = st.columns([1.5, 1.5])
with left:
    hist = px.histogram(
        artifacts.simulation.event_log,
        x="wait_time_minutes",
        nbins=20,
        title="Truck Wait Distribution",
        color_discrete_sequence=["#0b5c7a"],
    )
    hist.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(hist, use_container_width=True)
with right:
    stage = px.bar(
        artifacts.simulation.stage_metrics,
        x="stage",
        y="bottleneck_frequency",
        title="Bottleneck Frequency by Stage",
        color_discrete_sequence=["#f28f3b"],
    )
    stage.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(stage, use_container_width=True)

st.dataframe(artifacts.simulation.kpis, use_container_width=True, hide_index=True)
render_download(artifacts.simulation.event_log, "Download simulation event log", "simulation_event_log.csv")

if comparison_enabled:
    st.subheader("Baseline Delta")
    baseline_artifacts = run_mvp_pipeline(build_named_scenario("normal_operations"))
    baseline_kpis = baseline_artifacts.simulation.kpis.rename(columns={"value": "baseline_value"}).merge(
        artifacts.simulation.kpis.rename(columns={"value": "scenario_value"}),
        on="kpi",
        how="inner",
    )
    baseline_kpis["delta"] = baseline_kpis["scenario_value"] - baseline_kpis["baseline_value"]
    delta_fig = px.bar(
        baseline_kpis,
        x="kpi",
        y="delta",
        color="delta",
        color_continuous_scale=["#7a8b5a", "#f2c14e", "#f28f3b"],
        title="Scenario vs Normal Operations KPI Delta",
    )
    delta_fig.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0.75)")
    st.plotly_chart(delta_fig, use_container_width=True)
    st.dataframe(baseline_kpis, use_container_width=True, hide_index=True)
