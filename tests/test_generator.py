from src.config.settings import ScenarioConfig
from src.data.generator import SyntheticWarehouseDataGenerator


def test_generator_returns_expected_tables() -> None:
    config = ScenarioConfig(name="peak_season", horizon_days=30, random_seed=7)
    bundle = SyntheticWarehouseDataGenerator(config).generate()

    tables = bundle.to_dict()
    assert "inbound_trucks" in tables
    assert "historical_kpis" in tables
    assert len(bundle.inbound_trucks) > 0
    assert len(bundle.dock_doors) == 12
    assert {"truck_id", "actual_arrival_time", "labor_required"}.issubset(bundle.inbound_trucks.columns)


def test_labor_shortage_reduces_workers() -> None:
    normal = SyntheticWarehouseDataGenerator(
        ScenarioConfig(name="normal_operations", horizon_days=14, random_seed=42)
    ).generate()
    shortage = SyntheticWarehouseDataGenerator(
        ScenarioConfig(name="labor_shortage", horizon_days=14, random_seed=42)
    ).generate()

    assert len(shortage.workers) < len(normal.workers)
