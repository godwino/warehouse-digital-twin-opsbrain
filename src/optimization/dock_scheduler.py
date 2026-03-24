from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    from ortools.sat.python import cp_model
except ModuleNotFoundError:  # pragma: no cover - exercised indirectly in local fallback runs
    cp_model = None


@dataclass
class OptimizationArtifacts:
    dock_assignments: pd.DataFrame
    labor_plan: pd.DataFrame
    summary: pd.DataFrame


class DockSchedulingOptimizer:
    """Optimizes dock assignments, appointment timing, and shift-level labor posture."""

    def optimize(
        self,
        inbound_trucks: pd.DataFrame,
        dock_doors: pd.DataFrame,
        labor_shifts: pd.DataFrame,
    ) -> OptimizationArtifacts:
        window = self._prepare_window(inbound_trucks)
        active_docks = dock_doors[dock_doors["active"]].reset_index(drop=True)
        if cp_model is None:
            return self._heuristic_optimize(window, active_docks, labor_shifts)
        return self._cp_sat_optimize(window, active_docks, labor_shifts)

    def _prepare_window(self, inbound_trucks: pd.DataFrame) -> pd.DataFrame:
        window = inbound_trucks.sort_values(["appointment_time", "priority"]).head(24).copy().reset_index(drop=True)
        window["appointment_time"] = pd.to_datetime(window["appointment_time"])
        window["actual_arrival_time"] = pd.to_datetime(window["actual_arrival_time"])
        window["appointment_minute"] = (
            (window["appointment_time"] - window["appointment_time"].min()).dt.total_seconds() / 60
        ).astype(int)
        window["actual_arrival_minute"] = (
            (window["actual_arrival_time"] - window["appointment_time"].min()).dt.total_seconds() / 60
        ).astype(int)
        window["slot_length_minutes"] = np.ceil(window["unload_duration"] / 15).astype(int) * 15
        window["priority_weight"] = window["priority"].map({"standard": 1, "rush": 2, "critical": 4}).fillna(1).astype(int)
        window["compatibility_group"] = window.apply(self._required_dock_group, axis=1)
        return window

    def _cp_sat_optimize(
        self, window: pd.DataFrame, active_docks: pd.DataFrame, labor_shifts: pd.DataFrame
    ) -> OptimizationArtifacts:
        model = cp_model.CpModel()
        x: dict[tuple[int, int], cp_model.IntVar] = {}

        for i in range(len(window)):
            compatible_indices = self._compatible_dock_indices(window.iloc[i], active_docks)
            for j in compatible_indices:
                x[(i, j)] = model.NewBoolVar(f"truck_{i}_dock_{j}")
            model.Add(sum(x[(i, j)] for j in compatible_indices) == 1)

        shift_capacity = self._build_shift_capacity(active_docks, labor_shifts)
        for shift, cap in shift_capacity.items():
            truck_indices = [i for i in range(len(window)) if window.iloc[i]["shift"] == shift]
            if truck_indices:
                model.Add(sum(window.iloc[i]["labor_required"] * x[(i, j)] for i in truck_indices for j in self._compatible_dock_indices(window.iloc[i], active_docks)) <= cap)

        for j in range(len(active_docks)):
            dock_load_limit = max(1, int(np.ceil(len(window) / len(active_docks))))
            model.Add(sum(x[(i, j)] for i in range(len(window)) if (i, j) in x) <= dock_load_limit)

        objective_terms = []
        for i in range(len(window)):
            truck = window.iloc[i]
            for j in self._compatible_dock_indices(truck, active_docks):
                dock = active_docks.iloc[j]
                penalty = self._objective_penalty(truck, dock)
                objective_terms.append(x[(i, j)] * penalty)

        model.Minimize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 8
        solver.Solve(model)

        assignments = self._extract_assignments(window, active_docks, x, solver)
        labor_plan = self._build_labor_plan(window, labor_shifts)
        summary = self._build_summary(window, active_docks, assignments, "minimize_delay_overtime_congestion")
        return OptimizationArtifacts(assignments, labor_plan, summary)

    def _build_shift_capacity(self, active_docks: pd.DataFrame, labor_shifts: pd.DataFrame) -> dict[str, int]:
        dock_capacity = active_docks.groupby("shift")["dock_id"].count().mul(12).to_dict()
        labor_capacity = (
            labor_shifts.groupby("shift")["available_workers"].mean().mul(2.5).round().astype(int).to_dict()
        )
        shifts = set(dock_capacity) | set(labor_capacity)
        return {shift: max(4, min(dock_capacity.get(shift, 8), labor_capacity.get(shift, 8))) for shift in shifts}

    def _extract_assignments(
        self,
        window: pd.DataFrame,
        active_docks: pd.DataFrame,
        x: dict[tuple[int, int], object],
        solver: object,
    ) -> pd.DataFrame:
        rows = []
        for i in range(len(window)):
            truck = window.iloc[i]
            chosen_dock = None
            for j in range(len(active_docks)):
                if (i, j) in x and solver.Value(x[(i, j)]):
                    chosen_dock = active_docks.iloc[j]
                    break
            if chosen_dock is None:
                chosen_dock = active_docks.iloc[0]
            recommended_start = truck["appointment_time"] + pd.to_timedelta(
                self._reschedule_offset_minutes(truck, chosen_dock), unit="m"
            )
            rows.append(
                {
                    "truck_id": truck["truck_id"],
                    "recommended_dock_id": chosen_dock["dock_id"],
                    "original_dock_id": truck["dock_id"],
                    "priority": truck["priority"],
                    "compatibility_group": truck["compatibility_group"],
                    "delay_minutes": truck["delay_minutes"],
                    "recommended_start_time": recommended_start,
                    "recommended_reschedule_minutes": int(
                        (recommended_start - truck["appointment_time"]).total_seconds() / 60
                    ),
                    "labor_required": truck["labor_required"],
                    "estimated_congestion_risk": round(self._congestion_risk_score(truck, chosen_dock), 3),
                }
            )
        return pd.DataFrame(rows)

    def _build_summary(
        self, window: pd.DataFrame, active_docks: pd.DataFrame, assignments: pd.DataFrame, objective: str
    ) -> pd.DataFrame:
        estimated_delay_reduction = max(
            0,
            int(
                window["delay_minutes"].sum()
                - np.maximum(
                    0,
                    assignments["delay_minutes"] + assignments["recommended_reschedule_minutes"].clip(lower=0) * 0.35,
                ).sum()
            ),
        )
        service_breach_risk = float((assignments["estimated_congestion_risk"] > 0.55).mean())
        return pd.DataFrame(
            [
                {
                    "objective": objective,
                    "trucks_optimized": len(window),
                    "active_docks": len(active_docks),
                    "estimated_delay_reduction_minutes": estimated_delay_reduction,
                    "service_breach_risk": round(service_breach_risk, 3),
                    "avg_reschedule_minutes": round(assignments["recommended_reschedule_minutes"].mean(), 2),
                }
            ]
        )

    def _required_dock_group(self, truck: pd.Series) -> str:
        if truck["temperature_class"] == "cold":
            return "cold"
        if truck["fragile_mix"] > 0.35:
            return "fragile"
        return "standard"

    def _compatible_dock_indices(self, truck: pd.Series, active_docks: pd.DataFrame) -> list[int]:
        group = truck["compatibility_group"]
        if group == "cold":
            compatible = active_docks.index[active_docks["dock_type"] == "cold"].tolist()
        elif group == "fragile":
            compatible = active_docks.index[active_docks["dock_type"].isin(["fragile", "standard"])].tolist()
        else:
            compatible = active_docks.index[active_docks["dock_type"] != "cold"].tolist()
        return compatible or active_docks.index.tolist()

    def _objective_penalty(self, truck: pd.Series, dock: pd.Series) -> int:
        compatibility_penalty = self._compatibility_penalty(truck, dock)
        reassignment_penalty = 0 if truck["dock_id"] == dock["dock_id"] else 10
        window_penalty = max(0, truck["actual_arrival_minute"] - truck["appointment_minute"]) // 5
        overtime_penalty = truck["labor_required"] * 6
        congestion_penalty = int(self._congestion_risk_score(truck, dock) * 35)
        return int(
            compatibility_penalty
            + reassignment_penalty
            + window_penalty
            + overtime_penalty
            + congestion_penalty
            - truck["priority_weight"] * 4
        )

    def _compatibility_penalty(self, truck: pd.Series, dock: pd.Series) -> int:
        if truck["temperature_class"] == "cold" and dock["dock_type"] != "cold":
            return 120
        if truck["fragile_mix"] > 0.35 and dock["dock_type"] == "cold":
            return 70
        if truck["fragile_mix"] > 0.35 and dock["dock_type"] == "standard":
            return 18
        return 0

    def _congestion_risk_score(self, truck: pd.Series, dock: pd.Series) -> float:
        dock_speed_penalty = 1 - min(1.0, dock["max_pallets_per_hour"] / max(truck["pallet_count"], 1))
        arrival_penalty = min(1.0, abs(truck["delay_minutes"]) / 60)
        load_penalty = min(1.0, truck["labor_required"] / 5)
        return float(np.clip(0.25 * dock_speed_penalty + 0.35 * arrival_penalty + 0.4 * load_penalty, 0, 1))

    def _reschedule_offset_minutes(self, truck: pd.Series, dock: pd.Series) -> int:
        offset = 0
        if truck["priority"] == "critical":
            offset -= 10
        if truck["delay_minutes"] > 25:
            offset += min(30, int(truck["delay_minutes"] * 0.4))
        if truck["temperature_class"] == "cold" and dock["dock_type"] == "cold":
            offset -= 5
        return offset

    def _build_labor_plan(self, inbound_trucks: pd.DataFrame, labor_shifts: pd.DataFrame) -> pd.DataFrame:
        demand = inbound_trucks.groupby("shift").agg(
            required_workers=("labor_required", "sum"),
            inbound_trucks=("truck_id", "count"),
            avg_priority_weight=("priority_weight", "mean"),
        )
        supply = labor_shifts.groupby("shift").agg(
            available_workers=("available_workers", "mean"),
            overtime_minutes=("overtime_minutes", "mean"),
        )
        plan = demand.merge(supply, on="shift", how="left").reset_index()
        plan["gap_workers"] = (plan["required_workers"] - plan["available_workers"]).round(1)
        plan["zone_focus"] = plan["shift"].map({"day": "receiving", "swing": "staging", "night": "putaway"}).fillna("receiving")
        plan["recommended_reassignment"] = plan["gap_workers"].apply(
            lambda gap: "add flex labor" if gap > 0 else "maintain staffing"
        )
        plan["overtime_risk"] = np.clip(
            (plan["required_workers"] / plan["available_workers"].clip(lower=1)) - 1,
            0,
            1,
        ).round(2)
        return plan

    def _heuristic_optimize(
        self, window: pd.DataFrame, active_docks: pd.DataFrame, labor_shifts: pd.DataFrame
    ) -> OptimizationArtifacts:
        assignments = []
        ordered_docks = active_docks.sort_values(["dock_type", "max_pallets_per_hour"], ascending=[True, False]).reset_index(drop=True)
        for _, truck in window.sort_values(["priority_weight", "appointment_time"], ascending=[False, True]).iterrows():
            compatible = ordered_docks.iloc[self._compatible_dock_indices(truck, ordered_docks)]
            compatible = compatible.copy()
            compatible["score"] = compatible.apply(lambda dock: self._objective_penalty(truck, dock), axis=1)
            chosen_dock = compatible.sort_values(["score", "max_pallets_per_hour"]).iloc[0]
            recommended_start = truck["appointment_time"] + pd.to_timedelta(
                self._reschedule_offset_minutes(truck, chosen_dock), unit="m"
            )
            assignments.append(
                {
                    "truck_id": truck["truck_id"],
                    "recommended_dock_id": chosen_dock["dock_id"],
                    "original_dock_id": truck["dock_id"],
                    "priority": truck["priority"],
                    "compatibility_group": truck["compatibility_group"],
                    "delay_minutes": truck["delay_minutes"],
                    "recommended_start_time": recommended_start,
                    "recommended_reschedule_minutes": int(
                        (recommended_start - truck["appointment_time"]).total_seconds() / 60
                    ),
                    "labor_required": truck["labor_required"],
                    "estimated_congestion_risk": round(self._congestion_risk_score(truck, chosen_dock), 3),
                }
            )
        assignment_frame = pd.DataFrame(assignments)
        labor_plan = self._build_labor_plan(window, labor_shifts)
        summary = self._build_summary(window, ordered_docks, assignment_frame, "heuristic_minimize_delay_overtime_congestion")
        return OptimizationArtifacts(assignment_frame, labor_plan, summary)
