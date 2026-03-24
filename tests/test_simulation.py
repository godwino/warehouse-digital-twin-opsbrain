from src.config.settings import ScenarioConfig
from src.data.generator import SyntheticWarehouseDataGenerator
from src.simulation.digital_twin import WarehouseDigitalTwin


def test_simulation_generates_kpis() -> None:
    scenario = ScenarioConfig(name="surge_inbound_day", horizon_days=21, random_seed=42)
    bundle = SyntheticWarehouseDataGenerator(scenario).generate()
    artifacts = WarehouseDigitalTwin().run(bundle.inbound_trucks, scenario)
    assert not artifacts.event_log.empty
    assert set(artifacts.kpis["kpi"]).issuperset({"average_truck_wait_time", "throughput"})
    assert {
        "staging_time_minutes",
        "putaway_wait_minutes",
        "replenishment_time_minutes",
        "total_cycle_minutes",
    }.issubset(artifacts.event_log.columns)
    assert set(artifacts.stage_metrics["stage"]).issuperset({"staging", "putaway", "replenishment"})
