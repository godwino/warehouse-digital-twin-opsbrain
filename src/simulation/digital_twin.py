from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    import simpy
except ModuleNotFoundError:  # pragma: no cover - exercised indirectly in local fallback runs
    simpy = None

from src.config.settings import ScenarioConfig


@dataclass
class SimulationArtifacts:
    event_log: pd.DataFrame
    kpis: pd.DataFrame
    stage_metrics: pd.DataFrame


class WarehouseDigitalTwin:
    """Simulates receiving, staging, putaway, and replenishment under shared resource contention."""

    def run(self, inbound_trucks: pd.DataFrame, scenario: ScenarioConfig) -> SimulationArtifacts:
        if simpy is None:
            return self._fallback_run(inbound_trucks, scenario)

        env = simpy.Environment()
        trucks = self._prepare_trucks(inbound_trucks)
        base_time = pd.to_datetime(trucks["actual_arrival_time"]).min()
        active_docks = max(1, int(trucks["dock_id"].nunique() * scenario.active_dock_ratio))
        receiving_workers = max(3, int(np.ceil(trucks["labor_required"].mean() * 2.2 * scenario.labor_availability_ratio)))
        putaway_workers = max(3, int(np.ceil(trucks["labor_required"].mean() * 1.8 * scenario.labor_availability_ratio)))
        replen_workers = max(2, int(np.ceil(trucks["labor_required"].mean() * 1.2 * scenario.labor_availability_ratio)))
        dock_resource = simpy.Resource(env, capacity=active_docks)
        receiving_resource = simpy.Resource(env, capacity=receiving_workers)
        putaway_resource = simpy.Resource(env, capacity=putaway_workers)
        replen_resource = simpy.Resource(env, capacity=replen_workers)
        staging_buffer = simpy.Container(env, init=80, capacity=140)

        records: list[dict[str, float | str]] = []

        def truck_process(truck: pd.Series) -> simpy.events.Event:
            arrival_offset = (
                pd.to_datetime(truck["actual_arrival_time"]) - base_time
            ).total_seconds() / 60
            yield env.timeout(max(0.0, arrival_offset - env.now))

            queue_enter = env.now
            with dock_resource.request() as dock_req, receiving_resource.request() as recv_req:
                yield dock_req & recv_req
                receiving_wait = env.now - queue_enter
                unload_time = self._compute_unload_time(truck, scenario)
                yield env.timeout(unload_time)

            staging_enter = env.now
            staging_units = max(2, int(np.ceil(truck["pallet_count"] / 4)))
            yield staging_buffer.put(min(staging_units, int(staging_buffer.capacity - staging_buffer.level)))
            staging_delay = max(0.0, (staging_buffer.level - 95) * 0.35)
            if staging_delay > 0:
                yield env.timeout(staging_delay)

            with putaway_resource.request() as put_req:
                putaway_queue_start = env.now
                yield put_req
                putaway_wait = env.now - putaway_queue_start
                putaway_time = self._compute_putaway_time(truck, staging_buffer.level, scenario)
                yield env.timeout(putaway_time)

            with replen_resource.request() as repl_req:
                repl_queue_start = env.now
                yield repl_req
                replen_wait = env.now - repl_queue_start
                replen_time = self._compute_replenishment_time(truck, scenario)
                yield env.timeout(replen_time)

            yield staging_buffer.get(min(staging_units, int(staging_buffer.level)))
            total_cycle = env.now - queue_enter
            records.append(
                {
                    "truck_id": truck["truck_id"],
                    "shift": truck["shift"],
                    "priority": truck["priority"],
                    "zone": truck["zone"],
                    "wait_time_minutes": round(receiving_wait, 2),
                    "unload_time_minutes": round(unload_time, 2),
                    "staging_time_minutes": round((env.now - staging_enter) - putaway_time - replen_time, 2),
                    "putaway_wait_minutes": round(putaway_wait, 2),
                    "putaway_time_minutes": round(putaway_time, 2),
                    "replenishment_wait_minutes": round(replen_wait, 2),
                    "replenishment_time_minutes": round(replen_time, 2),
                    "total_cycle_minutes": round(total_cycle, 2),
                    "service_level_breach": int(total_cycle > 210 or receiving_wait > 45),
                    "dock_busy": dock_resource.count,
                    "receiving_busy": receiving_resource.count,
                    "putaway_busy": putaway_resource.count,
                    "replenishment_busy": replen_resource.count,
                    "staging_level": float(staging_buffer.level),
                }
            )

        for _, truck in trucks.iterrows():
            env.process(truck_process(truck))

        env.run()
        event_log = pd.DataFrame(records).sort_values("truck_id").reset_index(drop=True)
        kpis = self._build_kpis(
            event_log,
            active_docks=active_docks,
            receiving_workers=receiving_workers,
            putaway_workers=putaway_workers,
            replen_workers=replen_workers,
        )
        stage_metrics = self._build_stage_metrics(event_log)
        return SimulationArtifacts(event_log=event_log, kpis=kpis, stage_metrics=stage_metrics)

    def _prepare_trucks(self, inbound_trucks: pd.DataFrame) -> pd.DataFrame:
        trucks = inbound_trucks.sort_values("actual_arrival_time").head(72).copy().reset_index(drop=True)
        trucks["actual_arrival_time"] = pd.to_datetime(trucks["actual_arrival_time"])
        trucks["appointment_time"] = pd.to_datetime(trucks["appointment_time"])
        return trucks

    def _compute_unload_time(self, truck: pd.Series, scenario: ScenarioConfig) -> float:
        time = float(truck["unload_duration"])
        time *= 1.0 + max(0, truck["fragile_mix"] - 0.2) * 0.45
        if truck["temperature_class"] == "cold":
            time *= 1.08
        time *= 1.0 + max(0, 1 - scenario.labor_availability_ratio) * 0.28
        return round(time, 2)

    def _compute_putaway_time(self, truck: pd.Series, staging_level: float, scenario: ScenarioConfig) -> float:
        base = truck["pallet_count"] * 0.82 + (12 if truck["zone"] in {"bulk", "cold_store"} else 6)
        congestion_penalty = max(0.0, staging_level - 95) * 0.22
        fragile_penalty = truck["fragile_mix"] * 10
        dock_penalty = max(0.0, 1 - scenario.active_dock_ratio) * 4
        return round(base + congestion_penalty + fragile_penalty + dock_penalty, 2)

    def _compute_replenishment_time(self, truck: pd.Series, scenario: ScenarioConfig) -> float:
        base = truck["pallet_count"] * 0.28 + (5 if truck["priority"] == "critical" else 2)
        if truck["zone"] == "forward_pick":
            base += 4
        base *= 1.0 + max(0, 1 - scenario.labor_availability_ratio) * 0.12
        return round(base, 2)

    def _build_kpis(
        self,
        event_log: pd.DataFrame,
        active_docks: int,
        receiving_workers: int,
        putaway_workers: int,
        replen_workers: int,
    ) -> pd.DataFrame:
        avg_wait = event_log["wait_time_minutes"].mean()
        avg_unload = event_log["unload_time_minutes"].mean()
        avg_cycle = event_log["total_cycle_minutes"].mean()
        throughput = len(event_log)
        service_level = 1 - event_log["service_level_breach"].mean()
        dock_utilization = min(0.99, throughput / max(active_docks * 10, 1))
        labor_utilization = min(
            0.99,
            throughput / max((receiving_workers + putaway_workers + replen_workers) * 1.3, 1),
        )
        queue_proxy = (
            (event_log["wait_time_minutes"] > 20).sum()
            + (event_log["putaway_wait_minutes"] > 15).sum()
            + (event_log["replenishment_wait_minutes"] > 10).sum()
        ) / 6
        cost_estimate = (
            throughput * 54
            + avg_wait * 11
            + event_log["putaway_time_minutes"].mean() * 4
            + event_log["replenishment_time_minutes"].mean() * 3
        )
        return pd.DataFrame(
            [
                {"kpi": "average_truck_wait_time", "value": round(avg_wait, 2)},
                {"kpi": "average_unload_time", "value": round(avg_unload, 2)},
                {"kpi": "average_total_cycle_time", "value": round(avg_cycle, 2)},
                {"kpi": "dock_utilization", "value": round(dock_utilization, 2)},
                {"kpi": "labor_utilization", "value": round(labor_utilization, 2)},
                {"kpi": "queue_length_proxy", "value": round(queue_proxy, 2)},
                {"kpi": "throughput", "value": throughput},
                {"kpi": "cost_estimate", "value": round(cost_estimate, 2)},
                {"kpi": "service_level_attainment", "value": round(service_level, 3)},
            ]
        )

    def _build_stage_metrics(self, event_log: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "stage": "receiving_queue",
                    "avg_minutes": round(event_log["wait_time_minutes"].mean(), 2),
                    "bottleneck_frequency": round((event_log["wait_time_minutes"] > 30).mean(), 3),
                },
                {
                    "stage": "staging",
                    "avg_minutes": round(event_log["staging_time_minutes"].mean(), 2),
                    "bottleneck_frequency": round((event_log["staging_time_minutes"] > 25).mean(), 3),
                },
                {
                    "stage": "putaway",
                    "avg_minutes": round(event_log["putaway_time_minutes"].mean(), 2),
                    "bottleneck_frequency": round(
                        ((event_log["putaway_time_minutes"] + event_log["putaway_wait_minutes"]) > 45).mean(), 3
                    ),
                },
                {
                    "stage": "replenishment",
                    "avg_minutes": round(event_log["replenishment_time_minutes"].mean(), 2),
                    "bottleneck_frequency": round(
                        ((event_log["replenishment_time_minutes"] + event_log["replenishment_wait_minutes"]) > 22).mean(), 3
                    ),
                },
            ]
        )

    def _fallback_run(self, inbound_trucks: pd.DataFrame, scenario: ScenarioConfig) -> SimulationArtifacts:
        trucks = self._prepare_trucks(inbound_trucks)
        active_docks = max(1, int(trucks["dock_id"].nunique() * scenario.active_dock_ratio))
        workers = max(4, int(trucks["labor_required"].mean() * 3 * scenario.labor_availability_ratio))
        trucks["sequence"] = range(len(trucks))
        trucks["wait_time_minutes"] = (
            (trucks["sequence"] / active_docks) * (1.45 - scenario.active_dock_ratio) * 9
            + trucks["delay_minutes"] * 0.42
        ).round(2)
        trucks["unload_time_minutes"] = trucks.apply(lambda row: self._compute_unload_time(row, scenario), axis=1)
        trucks["staging_time_minutes"] = (
            (trucks["pallet_count"] * 0.18) + np.maximum(0, trucks["sequence"] - 20) * 0.6
        ).round(2)
        trucks["putaway_wait_minutes"] = (np.maximum(0, trucks["sequence"] - 16) * 0.55).round(2)
        trucks["putaway_time_minutes"] = trucks.apply(
            lambda row: self._compute_putaway_time(row, 90 + row["sequence"] * 0.3, scenario), axis=1
        )
        trucks["replenishment_wait_minutes"] = (np.maximum(0, trucks["sequence"] - 28) * 0.28).round(2)
        trucks["replenishment_time_minutes"] = trucks.apply(
            lambda row: self._compute_replenishment_time(row, scenario), axis=1
        )
        trucks["total_cycle_minutes"] = (
            trucks["wait_time_minutes"]
            + trucks["unload_time_minutes"]
            + trucks["staging_time_minutes"]
            + trucks["putaway_wait_minutes"]
            + trucks["putaway_time_minutes"]
            + trucks["replenishment_wait_minutes"]
            + trucks["replenishment_time_minutes"]
        ).round(2)
        trucks["service_level_breach"] = (
            (trucks["wait_time_minutes"] > 45) | (trucks["total_cycle_minutes"] > 210)
        ).astype(int)

        event_log = trucks[
            [
                "truck_id",
                "shift",
                "priority",
                "zone",
                "wait_time_minutes",
                "unload_time_minutes",
                "staging_time_minutes",
                "putaway_wait_minutes",
                "putaway_time_minutes",
                "replenishment_wait_minutes",
                "replenishment_time_minutes",
                "total_cycle_minutes",
                "service_level_breach",
            ]
        ].copy()
        event_log["dock_busy"] = active_docks
        event_log["receiving_busy"] = workers
        event_log["putaway_busy"] = max(3, int(workers * 0.8))
        event_log["replenishment_busy"] = max(2, int(workers * 0.5))
        event_log["staging_level"] = (80 + np.minimum(55, trucks["sequence"] * 0.9)).round(1)
        kpis = self._build_kpis(
            event_log,
            active_docks=active_docks,
            receiving_workers=workers,
            putaway_workers=max(3, int(workers * 0.8)),
            replen_workers=max(2, int(workers * 0.5)),
        )
        stage_metrics = self._build_stage_metrics(event_log)
        return SimulationArtifacts(event_log=event_log, kpis=kpis, stage_metrics=stage_metrics)
