from __future__ import annotations

import pandas as pd


def generate_recommendations(
    bottlenecks: pd.DataFrame,
    optimization_plan: pd.DataFrame,
    congestion_forecast: pd.DataFrame,
) -> pd.DataFrame:
    recommendations: list[dict[str, str | float]] = []

    for _, row in optimization_plan[optimization_plan["gap_workers"] > 0].iterrows():
        recommendations.append(
            {
                "recommendation": f"Add {int(round(max(1, row['gap_workers'])))} workers to {row['shift']} shift receiving",
                "reason": "Labor demand exceeds available staffing in optimized plan.",
                "expected_impact": "Reduce queue growth and overtime pressure.",
                "confidence": 0.82,
                "severity": min(1.0, float(row["gap_workers"]) / 6),
                "affected_kpi": "average_truck_wait_time",
            }
        )

    hotspot = congestion_forecast.sort_values("predicted_congestion_probability", ascending=False).head(2)
    for _, row in hotspot.iterrows():
        recommendations.append(
            {
                "recommendation": f"Flag {int(row['hour_of_day']):02d}:00 window as congestion hotspot and pre-stage labor",
                "reason": "Forecasted congestion probability is elevated for this hour.",
                "expected_impact": "Improve dock flow and service level attainment.",
                "confidence": round(float(row["predicted_congestion_probability"]), 2),
                "severity": round(float(row["predicted_congestion_probability"]), 2),
                "affected_kpi": "dock_utilization",
            }
        )

    for _, row in bottlenecks.head(3).iterrows():
        if row["area"] == "putaway":
            recommendations.append(
                {
                    "recommendation": "Move high-velocity SKUs closer to putaway target zones",
                    "reason": "Putaway cycle time is emerging as a recurring bottleneck.",
                    "expected_impact": "Reduce downstream travel time and staging congestion.",
                    "confidence": 0.74,
                    "severity": round(float(row["severity"]), 2),
                    "affected_kpi": "throughput",
                }
            )
        if row["area"] == "receiving_queue":
            recommendations.append(
                {
                    "recommendation": "Reschedule late-arriving trucks and use overflow staging during peak windows",
                    "reason": "Receiving queue waits are the dominant simulated bottleneck.",
                    "expected_impact": "Lower truck wait time and service-level breaches.",
                    "confidence": 0.79,
                    "severity": round(float(row["severity"]), 2),
                    "affected_kpi": "service_level_attainment",
                }
            )

    frame = pd.DataFrame(recommendations).drop_duplicates(subset=["recommendation"])
    return frame.sort_values(["severity", "confidence"], ascending=False).reset_index(drop=True)
