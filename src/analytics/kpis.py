from __future__ import annotations

import pandas as pd


def summarize_bottlenecks(
    simulation_stage_metrics: pd.DataFrame, forecast_risk: pd.DataFrame, optimization_labor: pd.DataFrame
) -> pd.DataFrame:
    top_risk = forecast_risk.sort_values("predicted_congestion_probability", ascending=False).head(4).copy()
    labor_gaps = optimization_labor[optimization_labor["gap_workers"] > 0].copy()
    rows = []
    for _, row in simulation_stage_metrics.iterrows():
        rows.append(
            {
                "source": "simulation",
                "area": row["stage"],
                "severity": row["bottleneck_frequency"],
                "metric": row["avg_minutes"],
            }
        )
    for _, row in top_risk.iterrows():
        rows.append(
            {
                "source": "forecast",
                "area": f"hour_{int(row['hour_of_day']):02d}",
                "severity": row["predicted_congestion_probability"],
                "metric": row["inbound_trucks"],
            }
        )
    for _, row in labor_gaps.iterrows():
        rows.append(
            {
                "source": "labor_plan",
                "area": row["shift"],
                "severity": row["gap_workers"],
                "metric": row["required_workers"],
            }
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values("severity", ascending=False).reset_index(drop=True)
