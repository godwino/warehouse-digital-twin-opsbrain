from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.features.engineering import create_daily_volume_features, create_hourly_workload_profile
from src.forecasting.metrics import mean_absolute_percentage_error


@dataclass
class ForecastArtifacts:
    daily_forecast: pd.DataFrame
    hourly_workload_forecast: pd.DataFrame
    labor_demand_forecast: pd.DataFrame
    congestion_risk_forecast: pd.DataFrame
    evaluation: pd.DataFrame


class ForecastingEngine:
    """Baseline plus feature-based forecasting for warehouse workload planning."""

    def fit_predict(self, historical_kpis: pd.DataFrame, inbound_trucks: pd.DataFrame) -> ForecastArtifacts:
        daily_features = create_daily_volume_features(historical_kpis)
        hourly_profile = create_hourly_workload_profile(inbound_trucks)

        daily_forecast, evaluation = self._forecast_daily_volume(daily_features)
        hourly_workload_forecast = self._forecast_hourly_workload(hourly_profile)
        labor_demand_forecast = self._forecast_labor_demand(hourly_workload_forecast)
        congestion_risk_forecast = self._forecast_congestion_risk(hourly_profile)

        return ForecastArtifacts(
            daily_forecast=daily_forecast,
            hourly_workload_forecast=hourly_workload_forecast,
            labor_demand_forecast=labor_demand_forecast,
            congestion_risk_forecast=congestion_risk_forecast,
            evaluation=evaluation,
        )

    def _forecast_daily_volume(self, features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        train = features.iloc[:-14].copy()
        test = features.iloc[-14:].copy()
        model_features = [
            "day_of_week",
            "week_of_year",
            "month",
            "is_weekend",
            "lag_1",
            "lag_7",
            "rolling_mean_7",
            "rolling_mean_14",
            "rolling_delay_7",
            "peak_flag",
            "promo_flag",
            "holiday_peak_flag",
            "weather_disruption_flag",
            "carrier_concentration",
            "vendor_concentration",
            "daily_variability_index",
            "avg_pallet_count",
        ]
        baseline_pred = test["lag_7"].to_numpy()

        strong_model = RandomForestRegressor(n_estimators=250, random_state=42, max_depth=8)
        strong_model.fit(train[model_features], train["inbound_truck_volume"])
        strong_pred = strong_model.predict(test[model_features])

        evaluation = pd.DataFrame(
            [
                self._score_model("baseline_lag7", test["inbound_truck_volume"].to_numpy(), baseline_pred),
                self._score_model("random_forest", test["inbound_truck_volume"].to_numpy(), strong_pred),
            ]
        )

        future = features.tail(7).copy()
        future["date"] = future["date"] + pd.to_timedelta(7, unit="D")
        future_pred = strong_model.predict(future[model_features])
        forecast = pd.DataFrame(
            {
                "date": future["date"],
                "forecast_inbound_truck_volume": np.round(future_pred, 1),
                "baseline_reference": np.round(future["lag_7"].to_numpy(), 1),
            }
        )
        return forecast, evaluation

    def _forecast_hourly_workload(self, hourly_profile: pd.DataFrame) -> pd.DataFrame:
        frame = hourly_profile.copy()
        frame["hour_of_day"] = pd.to_datetime(frame["hour"]).dt.hour
        hour_means = frame.groupby("hour_of_day")[["inbound_trucks", "pallets", "labor_required"]].mean()
        next_day = hour_means.reset_index()
        next_day["forecast_hour"] = pd.date_range(pd.Timestamp.today().floor("D"), periods=len(next_day), freq="h")
        next_day["forecast_inbound_trucks"] = next_day["inbound_trucks"].round(1)
        next_day["forecast_pallets"] = next_day["pallets"].round(1)
        next_day["forecast_labor_required"] = next_day["labor_required"].round(1)
        return next_day[
            ["forecast_hour", "forecast_inbound_trucks", "forecast_pallets", "forecast_labor_required"]
        ]

    def _forecast_labor_demand(self, hourly_forecast: pd.DataFrame) -> pd.DataFrame:
        frame = hourly_forecast.copy()
        frame["shift"] = pd.to_datetime(frame["forecast_hour"]).dt.hour.map(
            lambda h: "day" if 6 <= h < 14 else ("swing" if 14 <= h < 22 else "night")
        )
        grouped = frame.groupby("shift").agg(
            expected_trucks=("forecast_inbound_trucks", "sum"),
            expected_pallets=("forecast_pallets", "sum"),
            labor_demand=("forecast_labor_required", "mean"),
        )
        grouped["recommended_workers"] = np.ceil(grouped["labor_demand"] * 1.15).astype(int)
        return grouped.reset_index()

    def _forecast_congestion_risk(self, hourly_profile: pd.DataFrame) -> pd.DataFrame:
        frame = hourly_profile.copy()
        frame["hour_of_day"] = pd.to_datetime(frame["hour"]).dt.hour
        frame["risk_label"] = (frame["congestion_risk"] > 0.35).astype(int)
        model = LogisticRegression(max_iter=500)
        model.fit(frame[["inbound_trucks", "pallets", "labor_required", "hour_of_day"]], frame["risk_label"])
        template = frame.groupby("hour_of_day")[
            ["inbound_trucks", "pallets", "labor_required"]
        ].mean().reset_index()
        template["predicted_congestion_probability"] = model.predict_proba(
            template[["inbound_trucks", "pallets", "labor_required", "hour_of_day"]]
        )[:, 1]
        return template

    def _score_model(self, model_name: str, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | str]:
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        return {
            "model": model_name,
            "mae": round(mean_absolute_error(y_true, y_pred), 3),
            "rmse": round(rmse, 3),
            "mape": round(mean_absolute_percentage_error(y_true, y_pred), 3),
        }
