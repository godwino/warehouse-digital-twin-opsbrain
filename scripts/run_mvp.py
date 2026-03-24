from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.config.settings import ScenarioConfig, get_settings
from src.utils.demo import run_mvp_pipeline


def main() -> None:
    settings = get_settings()
    scenario = ScenarioConfig()
    artifacts = run_mvp_pipeline(scenario)

    report_dir = settings.reports_dir / scenario.name
    report_dir.mkdir(parents=True, exist_ok=True)

    artifacts.forecasting.daily_forecast.to_csv(report_dir / "daily_forecast.csv", index=False)
    artifacts.forecasting.hourly_workload_forecast.to_csv(
        report_dir / "hourly_workload_forecast.csv", index=False
    )
    artifacts.forecasting.labor_demand_forecast.to_csv(report_dir / "labor_demand_forecast.csv", index=False)
    artifacts.forecasting.congestion_risk_forecast.to_csv(
        report_dir / "congestion_risk_forecast.csv", index=False
    )
    artifacts.forecasting.evaluation.to_csv(report_dir / "forecast_evaluation.csv", index=False)
    artifacts.optimization.dock_assignments.to_csv(report_dir / "dock_assignments.csv", index=False)
    artifacts.optimization.labor_plan.to_csv(report_dir / "labor_plan.csv", index=False)
    artifacts.optimization.summary.to_csv(report_dir / "optimization_summary.csv", index=False)
    artifacts.simulation.event_log.to_csv(report_dir / "simulation_event_log.csv", index=False)
    artifacts.simulation.kpis.to_csv(report_dir / "simulation_kpis.csv", index=False)
    artifacts.simulation.stage_metrics.to_csv(report_dir / "simulation_stage_metrics.csv", index=False)
    artifacts.bottlenecks.to_csv(report_dir / "bottlenecks.csv", index=False)
    artifacts.recommendations.to_csv(report_dir / "recommendations.csv", index=False)

    print(f"MVP outputs saved to: {report_dir}")


if __name__ == "__main__":
    main()
