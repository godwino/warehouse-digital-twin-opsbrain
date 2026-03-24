from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.config.settings import ScenarioConfig, get_settings


def build_markdown_report(report_dir: Path, scenario_name: str) -> str:
    kpis = pd.read_csv(report_dir / "simulation_kpis.csv")
    recs = pd.read_csv(report_dir / "recommendations.csv")
    evaluation = pd.read_csv(report_dir / "forecast_evaluation.csv")
    bottlenecks = pd.read_csv(report_dir / "bottlenecks.csv")

    kpi_map = dict(zip(kpis["kpi"], kpis["value"]))
    top_rec = recs.iloc[0]
    top_bottleneck = bottlenecks.iloc[0]
    best_model = evaluation.sort_values("rmse").iloc[0]

    lines = [
        "# HVDC OpsBrain Demo Report",
        "",
        f"Scenario: `{scenario_name}`",
        "",
        "## Summary",
        "",
        "This report captures the current MVP outputs for a local demo run of HVDC OpsBrain.",
        "",
        "## Key KPIs",
        "",
        f"- Service level attainment: `{kpi_map['service_level_attainment']:.1%}`",
        f"- Average truck wait time: `{kpi_map['average_truck_wait_time']:.2f}` minutes",
        f"- Average unload time: `{kpi_map['average_unload_time']:.2f}` minutes",
        f"- Dock utilization: `{kpi_map['dock_utilization']:.0%}`",
        f"- Labor utilization: `{kpi_map['labor_utilization']:.0%}`",
        f"- Throughput: `{int(kpi_map['throughput'])}` trucks",
        f"- Cost estimate: `${kpi_map['cost_estimate']:,.2f}`",
        "",
        "## Forecast Snapshot",
        "",
        f"- Best evaluated model: `{best_model['model']}`",
        f"- MAE: `{best_model['mae']:.2f}`",
        f"- RMSE: `{best_model['rmse']:.2f}`",
        f"- MAPE: `{best_model['mape']:.2f}%`",
        "",
        "## Bottleneck Snapshot",
        "",
        f"- Highest pressure area: `{top_bottleneck['area']}`",
        f"- Source: `{top_bottleneck['source']}`",
        f"- Severity: `{top_bottleneck['severity']:.2f}`",
        f"- Metric: `{top_bottleneck['metric']:.2f}`",
        "",
        "## Lead Recommendation",
        "",
        f"- Action: `{top_rec['recommendation']}`",
        f"- Reason: {top_rec['reason']}",
        f"- Expected impact: {top_rec['expected_impact']}",
        f"- Confidence: `{top_rec['confidence']:.0%}`",
        f"- Affected KPI: `{top_rec['affected_kpi']}`",
        "",
        "## Notes",
        "",
        "- This project uses synthetic data, so very low forecast error can occur when the generated patterns are highly regular.",
        "- Exported CSVs in the same report folder provide the full underlying detail for deeper analysis.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    settings = get_settings()
    scenario = ScenarioConfig()
    report_dir = settings.reports_dir / scenario.name
    report_dir.mkdir(parents=True, exist_ok=True)
    markdown = build_markdown_report(report_dir, scenario.name)
    output_path = report_dir / "demo_report.md"
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Demo report saved to: {output_path}")


if __name__ == "__main__":
    main()
