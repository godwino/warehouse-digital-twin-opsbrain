from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from src.config.settings import ScenarioConfig


@dataclass
class WarehouseDataBundle:
    inbound_trucks: pd.DataFrame
    truck_arrivals: pd.DataFrame
    dock_doors: pd.DataFrame
    skus: pd.DataFrame
    sku_velocity_profiles: pd.DataFrame
    labor_shifts: pd.DataFrame
    workers: pd.DataFrame
    unload_tasks: pd.DataFrame
    putaway_tasks: pd.DataFrame
    replenishment_tasks: pd.DataFrame
    zones: pd.DataFrame
    equipment: pd.DataFrame
    historical_kpis: pd.DataFrame

    def to_dict(self) -> dict[str, pd.DataFrame]:
        return self.__dict__


class SyntheticWarehouseDataGenerator:
    """Creates a realistic but compact warehouse operations dataset."""

    carriers = ["DHL", "FedEx", "XPO", "Maersk", "CJ Logistics"]
    vendors = ["ABB", "Siemens", "Hitachi", "Schneider", "GE", "Eaton"]
    temp_classes = ["ambient", "controlled", "cold"]
    priorities = ["standard", "rush", "critical"]
    worker_skills = ["receiving", "forklift", "putaway", "replenishment", "fragile_handling"]
    shifts = ["day", "swing", "night"]
    zones = ["receiving", "staging", "bulk", "forward_pick", "fragile", "cold_store"]
    equipment_types = ["forklift", "pallet_jack", "clamp_truck", "reach_truck"]

    def __init__(self, config: ScenarioConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.random_seed)

    def generate(self) -> WarehouseDataBundle:
        dates = pd.date_range("2025-01-01", periods=self.config.horizon_days, freq="D")
        zones = self._generate_zones()
        dock_doors = self._generate_dock_doors()
        skus = self._generate_skus()
        sku_velocity = self._generate_sku_velocity_profiles(skus)
        workers = self._generate_workers()
        labor_shifts = self._generate_labor_shifts(dates, workers)
        inbound_trucks = self._generate_inbound_trucks(dates, dock_doors)
        truck_arrivals = self._generate_truck_arrivals(inbound_trucks)
        unload_tasks = self._generate_unload_tasks(inbound_trucks)
        putaway_tasks = self._generate_putaway_tasks(unload_tasks, skus)
        replenishment_tasks = self._generate_replenishment_tasks(dates, skus)
        equipment = self._generate_equipment()
        historical_kpis = self._generate_historical_kpis(dates, inbound_trucks, labor_shifts)
        return WarehouseDataBundle(
            inbound_trucks=inbound_trucks,
            truck_arrivals=truck_arrivals,
            dock_doors=dock_doors,
            skus=skus,
            sku_velocity_profiles=sku_velocity,
            labor_shifts=labor_shifts,
            workers=workers,
            unload_tasks=unload_tasks,
            putaway_tasks=putaway_tasks,
            replenishment_tasks=replenishment_tasks,
            zones=zones,
            equipment=equipment,
            historical_kpis=historical_kpis,
        )

    def _scenario_adjustments(self) -> dict[str, Any]:
        base = {
            "volume_multiplier": self.config.inbound_volume_multiplier,
            "labor_ratio": self.config.labor_availability_ratio,
            "active_dock_ratio": self.config.active_dock_ratio,
            "fragile_delta": self.config.fragile_mix_delta,
            "priority_delta": self.config.priority_mix_delta,
        }
        scenario = self.config.name
        if scenario == "peak_season":
            base["volume_multiplier"] *= 1.35
            base["priority_delta"] += 0.05
        elif scenario == "labor_shortage":
            base["labor_ratio"] *= 0.75
        elif scenario == "dock_outage":
            base["active_dock_ratio"] *= 0.75
        elif scenario == "surge_inbound_day":
            base["volume_multiplier"] *= 1.5
        elif scenario == "fragile_load_mix_increase":
            base["fragile_delta"] += 0.2
        return base

    def _generate_zones(self) -> pd.DataFrame:
        capacities = [240, 180, 400, 280, 120, 90]
        return pd.DataFrame(
            {
                "zone": self.zones,
                "throughput_per_hour": capacities,
                "congestion_threshold": [0.82, 0.8, 0.88, 0.84, 0.7, 0.68],
            }
        )

    def _generate_dock_doors(self) -> pd.DataFrame:
        adjustments = self._scenario_adjustments()
        total_doors = 12
        active_count = max(1, int(round(total_doors * adjustments["active_dock_ratio"])))
        door_types = ["standard", "standard", "fragile", "fragile", "cold"] + ["standard"] * 7
        records = []
        for i in range(total_doors):
            records.append(
                {
                    "dock_id": f"D{i + 1:02d}",
                    "dock_type": door_types[i],
                    "active": i < active_count,
                    "max_pallets_per_hour": int(self.rng.integers(18, 30)),
                    "shift": self.shifts[i % len(self.shifts)],
                }
            )
        return pd.DataFrame(records)

    def _generate_skus(self) -> pd.DataFrame:
        sku_count = 220
        records = []
        for idx in range(sku_count):
            velocity = self.rng.choice(["A", "B", "C"], p=[0.2, 0.35, 0.45])
            records.append(
                {
                    "sku_id": f"SKU-{idx + 1:04d}",
                    "vendor": self.rng.choice(self.vendors),
                    "zone": self.rng.choice(self.zones[2:]),
                    "velocity_class": velocity,
                    "cube": round(float(self.rng.uniform(0.05, 1.5)), 3),
                    "weight": round(float(self.rng.uniform(1, 55)), 2),
                    "fragile_flag": int(self.rng.random() < 0.15),
                    "temperature_class": self.rng.choice(self.temp_classes, p=[0.7, 0.2, 0.1]),
                }
            )
        return pd.DataFrame(records)

    def _generate_sku_velocity_profiles(self, skus: pd.DataFrame) -> pd.DataFrame:
        velocity_map = {"A": 48, "B": 22, "C": 9}
        profiles = skus[["sku_id", "velocity_class"]].copy()
        profiles["avg_daily_picks"] = profiles["velocity_class"].map(velocity_map)
        profiles["replenishment_trigger"] = profiles["velocity_class"].map({"A": 0.55, "B": 0.4, "C": 0.25})
        return profiles

    def _generate_workers(self) -> pd.DataFrame:
        adjustments = self._scenario_adjustments()
        base_workers = max(18, int(round(42 * adjustments["labor_ratio"])))
        records = []
        for idx in range(base_workers):
            skill = self.rng.choice(self.worker_skills, p=[0.28, 0.24, 0.2, 0.18, 0.1])
            records.append(
                {
                    "worker_id": f"W{idx + 1:03d}",
                    "worker_skill": skill,
                    "shift_preference": self.rng.choice(self.shifts, p=[0.45, 0.35, 0.2]),
                    "hourly_rate": round(float(self.rng.uniform(24, 38)), 2),
                    "productivity_index": round(float(self.rng.uniform(0.8, 1.2)), 2),
                }
            )
        return pd.DataFrame(records)

    def _generate_labor_shifts(self, dates: pd.DatetimeIndex, workers: pd.DataFrame) -> pd.DataFrame:
        records = []
        for day in dates:
            for shift in self.shifts:
                assigned = workers[workers["shift_preference"] == shift]
                available = max(4, int(round(len(assigned) * self.rng.uniform(0.78, 0.96))))
                overtime = max(0.0, (0.84 - available / max(len(assigned), 1)) * 120)
                records.append(
                    {
                        "date": day,
                        "shift": shift,
                        "available_workers": available,
                        "planned_hours": available * 8,
                        "overtime_minutes": round(overtime, 1),
                        "labor_cost": round(float(available * self.rng.uniform(210, 305)), 2),
                    }
                )
        return pd.DataFrame(records)

    def _generate_inbound_trucks(self, dates: pd.DatetimeIndex, dock_doors: pd.DataFrame) -> pd.DataFrame:
        adjustments = self._scenario_adjustments()
        records = []
        for day in dates:
            weekday_factor = 1.2 if day.weekday() in (1, 2, 3) else 0.85
            peak_factor = 1.15 if day.month in (9, 10, 11) else 1.0
            cycle_factor = 1 + 0.12 * np.sin((2 * np.pi * day.dayofyear) / 28)
            month_end_factor = 1.18 if day.day >= 25 else 1.0
            promo_flag = int(day.dayofyear % 17 == 0 or self.rng.random() < 0.05)
            holiday_peak_flag = int((day.month, day.day) in {(1, 15), (5, 27), (9, 2), (11, 28), (12, 15)})
            weather_disruption_flag = int(self.rng.random() < 0.06)
            vendor_bias = 1 + self.rng.normal(0, 0.07)
            stochastic_shock = max(0.7, 1 + self.rng.normal(0, 0.11))
            mean_trucks = (
                18
                * weekday_factor
                * peak_factor
                * cycle_factor
                * month_end_factor
                * (1 + promo_flag * 0.12)
                * (1 + holiday_peak_flag * 0.18)
                * (1 - weather_disruption_flag * 0.09)
                * vendor_bias
                * stochastic_shock
                * adjustments["volume_multiplier"]
            )
            expected_trucks = max(8, int(self.rng.poisson(max(8.0, mean_trucks))))
            for truck_idx in range(expected_trucks):
                appointment_hour = int(self.rng.integers(5, 5 + self.config.operating_hours))
                appointment_time = day + timedelta(hours=appointment_hour, minutes=int(self.rng.integers(0, 60)))
                pallet_count = int(self.rng.integers(8, 36))
                fragile_mix = min(0.85, float(self.rng.beta(2, 8) + adjustments["fragile_delta"]))
                critical_share = min(0.24, 0.08 + adjustments["priority_delta"])
                standard_share = max(0.55, 0.8 - critical_share)
                rush_share = 1.0 - standard_share - critical_share
                priority = self.rng.choice(self.priorities, p=[standard_share, rush_share, critical_share])
                delay_mean = 18 if priority == "standard" else 10
                delay = max(
                    0,
                    int(
                        self.rng.normal(
                            delay_mean + weather_disruption_flag * 9 + promo_flag * 4,
                            16 + holiday_peak_flag * 4,
                        )
                    ),
                )
                dock_candidates = dock_doors[dock_doors["active"]]
                dock_id = dock_candidates.sample(1, random_state=int(self.rng.integers(0, 1_000_000)))[
                    "dock_id"
                ].iloc[0]
                records.append(
                    {
                        "truck_id": f"{day.strftime('%Y%m%d')}-{truck_idx + 1:03d}",
                        "carrier": self.rng.choice(self.carriers),
                        "vendor": self.rng.choice(self.vendors),
                        "appointment_time": appointment_time,
                        "actual_arrival_time": appointment_time + timedelta(minutes=delay),
                        "unload_duration": int(max(20, self.rng.normal(48 + pallet_count * 1.8, 12))),
                        "pallet_count": pallet_count,
                        "cube": round(float(pallet_count * self.rng.uniform(0.9, 1.8)), 2),
                        "weight": round(float(pallet_count * self.rng.uniform(120, 340)), 2),
                        "priority": priority,
                        "fragile_mix": round(fragile_mix, 3),
                        "temperature_class": self.rng.choice(self.temp_classes, p=[0.73, 0.18, 0.09]),
                        "dock_id": dock_id,
                        "shift": self.shifts[(appointment_hour // 8) % 3],
                        "zone": self.rng.choice(self.zones, p=[0.2, 0.18, 0.23, 0.22, 0.1, 0.07]),
                        "labor_required": max(2, int(round(pallet_count / 10))),
                        "congestion_flag": int(delay > 25 or pallet_count > 28),
                        "delay_minutes": delay,
                        "service_level_breach": int(delay > 45),
                        "promo_flag": promo_flag,
                        "holiday_peak_flag": holiday_peak_flag,
                        "weather_disruption_flag": weather_disruption_flag,
                    }
                )
        return pd.DataFrame(records)

    def _generate_truck_arrivals(self, inbound_trucks: pd.DataFrame) -> pd.DataFrame:
        frame = inbound_trucks[["truck_id", "appointment_time", "actual_arrival_time", "dock_id", "shift"]].copy()
        frame["arrival_delta_minutes"] = (
            frame["actual_arrival_time"] - frame["appointment_time"]
        ).dt.total_seconds() / 60
        frame["queue_entry_time"] = frame["actual_arrival_time"] + pd.to_timedelta(
            self.rng.integers(2, 20, size=len(frame)), unit="m"
        )
        return frame

    def _generate_unload_tasks(self, inbound_trucks: pd.DataFrame) -> pd.DataFrame:
        frame = inbound_trucks[
            ["truck_id", "dock_id", "shift", "pallet_count", "labor_required", "unload_duration", "priority"]
        ].copy()
        frame["task_id"] = [f"UNL-{i:05d}" for i in range(1, len(frame) + 1)]
        frame["task_type"] = "unload"
        frame["equipment_required"] = np.where(frame["pallet_count"] > 24, "forklift", "pallet_jack")
        return frame

    def _generate_putaway_tasks(self, unload_tasks: pd.DataFrame, skus: pd.DataFrame) -> pd.DataFrame:
        sample_skus = skus.sample(
            n=len(unload_tasks),
            replace=True,
            random_state=self.config.random_seed,
        ).reset_index(drop=True)
        frame = unload_tasks[["task_id", "truck_id", "pallet_count", "shift"]].copy().reset_index(drop=True)
        frame["putaway_task_id"] = [f"PUT-{i:05d}" for i in range(1, len(frame) + 1)]
        frame["sku_id"] = sample_skus["sku_id"]
        frame["zone"] = sample_skus["zone"]
        frame["travel_minutes"] = self.rng.integers(6, 24, size=len(frame))
        frame["labor_required"] = np.maximum(1, np.ceil(frame["pallet_count"] / 14)).astype(int)
        return frame

    def _generate_replenishment_tasks(self, dates: pd.DatetimeIndex, skus: pd.DataFrame) -> pd.DataFrame:
        records = []
        task_counter = 1
        for day in dates:
            replen_count = int(self.rng.integers(12, 28))
            sample = skus.sample(replen_count, replace=True, random_state=int(self.rng.integers(0, 1_000_000)))
            for _, row in sample.iterrows():
                records.append(
                    {
                        "replenishment_task_id": f"REP-{task_counter:05d}",
                        "date": day,
                        "sku_id": row["sku_id"],
                        "zone": row["zone"],
                        "priority": self.rng.choice(["routine", "hot"], p=[0.82, 0.18]),
                        "labor_required": int(self.rng.integers(1, 3)),
                        "task_minutes": int(self.rng.integers(10, 35)),
                    }
                )
                task_counter += 1
        return pd.DataFrame(records)

    def _generate_equipment(self) -> pd.DataFrame:
        records = []
        for idx in range(22):
            records.append(
                {
                    "equipment_id": f"E{idx + 1:03d}",
                    "equipment_type": self.rng.choice(self.equipment_types, p=[0.36, 0.32, 0.12, 0.2]),
                    "available": int(self.rng.random() > 0.08),
                    "zone": self.rng.choice(self.zones),
                }
            )
        return pd.DataFrame(records)

    def _generate_historical_kpis(
        self, dates: pd.DatetimeIndex, inbound_trucks: pd.DataFrame, labor_shifts: pd.DataFrame
    ) -> pd.DataFrame:
        inbound = inbound_trucks.copy()
        inbound["date"] = pd.to_datetime(inbound["appointment_time"]).dt.normalize()
        by_day = inbound.groupby("date").agg(
            inbound_truck_volume=("truck_id", "count"),
            avg_delay_minutes=("delay_minutes", "mean"),
            avg_unload_minutes=("unload_duration", "mean"),
            congestion_events=("congestion_flag", "sum"),
            service_breaches=("service_level_breach", "sum"),
            promo_flag=("promo_flag", "max"),
            holiday_peak_flag=("holiday_peak_flag", "max"),
            weather_disruption_flag=("weather_disruption_flag", "max"),
            carrier_count=("carrier", "nunique"),
            vendor_count=("vendor", "nunique"),
            avg_pallet_count=("pallet_count", "mean"),
        )
        labor = labor_shifts.copy()
        labor["date"] = pd.to_datetime(labor["date"]).dt.normalize()
        labor_by_day = labor.groupby("date").agg(
            available_workers=("available_workers", "sum"),
            overtime_minutes=("overtime_minutes", "sum"),
            labor_cost=("labor_cost", "sum"),
        )
        frame = (
            by_day.reset_index()
            .merge(labor_by_day.reset_index(), on="date", how="left")
            .sort_values("date")
        )
        frame["throughput_pallets"] = frame["inbound_truck_volume"] * self.rng.integers(16, 24, size=len(frame))
        frame["dock_utilization"] = np.clip(frame["inbound_truck_volume"] / 24, 0.35, 0.98)
        frame["labor_utilization"] = np.clip(
            frame["throughput_pallets"] / (frame["available_workers"] * 18), 0.4, 1.15
        )
        frame["service_level_attainment"] = 1 - frame["service_breaches"] / frame["inbound_truck_volume"].clip(lower=1)
        frame["cost_estimate"] = frame["labor_cost"] + frame["overtime_minutes"] * 0.9
        frame["peak_flag"] = frame["date"].apply(lambda d: pd.Timestamp(d).month in (9, 10, 11)).astype(int)
        frame["carrier_concentration"] = (frame["carrier_count"] / 5).round(3)
        frame["vendor_concentration"] = (frame["vendor_count"] / 6).round(3)
        frame["daily_variability_index"] = (
            frame["avg_delay_minutes"] * 0.04
            + frame["avg_pallet_count"] * 0.03
            + frame["weather_disruption_flag"] * 0.25
        ).round(3)
        return frame
