from __future__ import annotations

import pandas as pd


def create_daily_volume_features(historical_kpis: pd.DataFrame) -> pd.DataFrame:
    frame = historical_kpis.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").reset_index(drop=True)
    frame["day_of_week"] = frame["date"].dt.dayofweek
    frame["day_name"] = frame["date"].dt.day_name()
    frame["week_of_year"] = frame["date"].dt.isocalendar().week.astype(int)
    frame["month"] = frame["date"].dt.month
    frame["is_weekend"] = frame["day_of_week"].isin([5, 6]).astype(int)
    frame["lag_1"] = frame["inbound_truck_volume"].shift(1)
    frame["lag_7"] = frame["inbound_truck_volume"].shift(7)
    frame["rolling_mean_7"] = frame["inbound_truck_volume"].rolling(7, min_periods=1).mean().shift(1)
    frame["rolling_mean_14"] = frame["inbound_truck_volume"].rolling(14, min_periods=1).mean().shift(1)
    frame["rolling_delay_7"] = frame["avg_delay_minutes"].rolling(7, min_periods=1).mean().shift(1)
    frame["peak_flag"] = frame["peak_flag"].astype(int)
    for column in [
        "promo_flag",
        "holiday_peak_flag",
        "weather_disruption_flag",
        "carrier_concentration",
        "vendor_concentration",
        "daily_variability_index",
        "avg_pallet_count",
    ]:
        if column not in frame:
            frame[column] = 0
    return frame.bfill().ffill()


def create_hourly_workload_profile(inbound_trucks: pd.DataFrame) -> pd.DataFrame:
    frame = inbound_trucks.copy()
    frame["appointment_time"] = pd.to_datetime(frame["appointment_time"])
    frame["hour"] = frame["appointment_time"].dt.floor("h")
    grouped = frame.groupby("hour").agg(
        inbound_trucks=("truck_id", "count"),
        pallets=("pallet_count", "sum"),
        labor_required=("labor_required", "sum"),
        congestion_events=("congestion_flag", "sum"),
    )
    grouped["congestion_risk"] = (
        grouped["congestion_events"] / grouped["inbound_trucks"].clip(lower=1)
    ).round(3)
    return grouped.reset_index()
