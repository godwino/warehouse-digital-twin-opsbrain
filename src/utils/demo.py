from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import uuid

import pandas as pd

from src.analytics.kpis import summarize_bottlenecks
from src.config.settings import ScenarioConfig, build_named_scenario, get_settings
from src.data.pipeline import build_synthetic_dataset
from src.database.sqlite_store import SQLiteStore
from src.forecasting.engine import ForecastArtifacts, ForecastingEngine
from src.optimization.dock_scheduler import DockSchedulingOptimizer, OptimizationArtifacts
from src.recommendations.engine import generate_recommendations
from src.simulation.digital_twin import SimulationArtifacts, WarehouseDigitalTwin


@dataclass
class MVPArtifacts:
    dataset: dict[str, pd.DataFrame]
    forecasting: ForecastArtifacts
    optimization: OptimizationArtifacts
    simulation: SimulationArtifacts
    bottlenecks: pd.DataFrame
    recommendations: pd.DataFrame


@dataclass
class ScenarioComparisonArtifacts:
    baseline_name: str
    comparison_name: str
    baseline: MVPArtifacts
    comparison: MVPArtifacts
    kpi_delta: pd.DataFrame
    stage_delta: pd.DataFrame
    recommendation_delta: pd.DataFrame


def run_mvp_pipeline(scenario: ScenarioConfig) -> MVPArtifacts:
    bundle = build_synthetic_dataset(scenario)
    forecasting = ForecastingEngine().fit_predict(bundle.historical_kpis, bundle.inbound_trucks)
    optimization = DockSchedulingOptimizer().optimize(
        bundle.inbound_trucks,
        bundle.dock_doors,
        bundle.labor_shifts,
    )
    simulation = WarehouseDigitalTwin().run(bundle.inbound_trucks, scenario)
    bottlenecks = summarize_bottlenecks(
        simulation.stage_metrics,
        forecasting.congestion_risk_forecast,
        optimization.labor_plan,
    )
    recommendations = generate_recommendations(
        bottlenecks,
        optimization.labor_plan,
        forecasting.congestion_risk_forecast,
    )
    artifacts = MVPArtifacts(
        dataset=bundle.to_dict(),
        forecasting=forecasting,
        optimization=optimization,
        simulation=simulation,
        bottlenecks=bottlenecks,
        recommendations=recommendations,
    )
    _persist_run_summary(scenario, artifacts)
    return artifacts


def compare_named_scenarios(
    baseline_name: str = "normal_operations",
    comparison_name: str = "labor_shortage",
) -> ScenarioComparisonArtifacts:
    baseline = run_mvp_pipeline(build_named_scenario(baseline_name))
    comparison = run_mvp_pipeline(build_named_scenario(comparison_name))
    kpi_delta = _build_kpi_delta(baseline.simulation.kpis, comparison.simulation.kpis)
    stage_delta = _build_stage_delta(baseline.simulation.stage_metrics, comparison.simulation.stage_metrics)
    recommendation_delta = _build_recommendation_delta(baseline.recommendations, comparison.recommendations)
    return ScenarioComparisonArtifacts(
        baseline_name=baseline_name,
        comparison_name=comparison_name,
        baseline=baseline,
        comparison=comparison,
        kpi_delta=kpi_delta,
        stage_delta=stage_delta,
        recommendation_delta=recommendation_delta,
    )


def _build_kpi_delta(baseline_kpis: pd.DataFrame, comparison_kpis: pd.DataFrame) -> pd.DataFrame:
    frame = baseline_kpis.rename(columns={"value": "baseline_value"}).merge(
        comparison_kpis.rename(columns={"value": "comparison_value"}),
        on="kpi",
        how="inner",
    )
    frame["delta"] = frame["comparison_value"] - frame["baseline_value"]
    frame["delta_pct"] = (
        frame["delta"] / frame["baseline_value"].replace(0, 1)
    ).round(3)
    return frame.sort_values("kpi").reset_index(drop=True)


def _build_stage_delta(baseline_stage: pd.DataFrame, comparison_stage: pd.DataFrame) -> pd.DataFrame:
    frame = baseline_stage.rename(
        columns={
            "avg_minutes": "baseline_avg_minutes",
            "bottleneck_frequency": "baseline_bottleneck_frequency",
        }
    ).merge(
        comparison_stage.rename(
            columns={
                "avg_minutes": "comparison_avg_minutes",
                "bottleneck_frequency": "comparison_bottleneck_frequency",
            }
        ),
        on="stage",
        how="inner",
    )
    frame["avg_minutes_delta"] = frame["comparison_avg_minutes"] - frame["baseline_avg_minutes"]
    frame["bottleneck_delta"] = (
        frame["comparison_bottleneck_frequency"] - frame["baseline_bottleneck_frequency"]
    )
    return frame.sort_values("bottleneck_delta", ascending=False).reset_index(drop=True)


def _build_recommendation_delta(
    baseline_recommendations: pd.DataFrame, comparison_recommendations: pd.DataFrame
) -> pd.DataFrame:
    baseline_actions = set(baseline_recommendations["recommendation"])
    comparison_frame = comparison_recommendations.copy()
    comparison_frame["status_vs_baseline"] = comparison_frame["recommendation"].apply(
        lambda rec: "new_in_comparison" if rec not in baseline_actions else "shared"
    )
    return comparison_frame.sort_values(["status_vs_baseline", "severity"], ascending=[True, False]).reset_index(
        drop=True
    )


def load_run_history(limit: int = 12) -> pd.DataFrame:
    settings = get_settings()
    store = SQLiteStore(settings.db_path)
    history = store.load_table("scenario_runs")
    if history.empty:
        return history
    history["created_at"] = pd.to_datetime(history["created_at"])
    return history.sort_values("created_at", ascending=False).head(limit).reset_index(drop=True)


def _persist_run_summary(scenario: ScenarioConfig, artifacts: MVPArtifacts) -> None:
    settings = get_settings()
    store = SQLiteStore(settings.db_path)
    kpi_map = {row["kpi"]: row["value"] for _, row in artifacts.simulation.kpis.iterrows()}
    top_rec = (
        artifacts.recommendations.iloc[0]["recommendation"]
        if not artifacts.recommendations.empty
        else "No recommendation generated"
    )
    record = pd.DataFrame(
        [
            {
                "run_id": str(uuid.uuid4()),
                "created_at": datetime.now(UTC).isoformat(),
                "scenario_name": scenario.name,
                "scenario_params": json.dumps(scenario.model_dump(mode="json")),
                "inbound_volume_multiplier": scenario.inbound_volume_multiplier,
                "labor_availability_ratio": scenario.labor_availability_ratio,
                "active_dock_ratio": scenario.active_dock_ratio,
                "fragile_mix_delta": scenario.fragile_mix_delta,
                "priority_mix_delta": scenario.priority_mix_delta,
                "operating_hours": scenario.operating_hours,
                "service_level_attainment": kpi_map.get("service_level_attainment", 0.0),
                "average_truck_wait_time": kpi_map.get("average_truck_wait_time", 0.0),
                "average_total_cycle_time": kpi_map.get("average_total_cycle_time", 0.0),
                "dock_utilization": kpi_map.get("dock_utilization", 0.0),
                "labor_utilization": kpi_map.get("labor_utilization", 0.0),
                "throughput": kpi_map.get("throughput", 0.0),
                "cost_estimate": kpi_map.get("cost_estimate", 0.0),
                "top_recommendation": top_rec,
            }
        ]
    )
    store.append_table("scenario_runs", record)
