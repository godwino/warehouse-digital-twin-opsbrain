from src.config.settings import ScenarioConfig
from src.data.generator import SyntheticWarehouseDataGenerator
from src.optimization.dock_scheduler import DockSchedulingOptimizer


def test_optimizer_returns_assignments() -> None:
    bundle = SyntheticWarehouseDataGenerator(
        ScenarioConfig(name="dock_outage", horizon_days=30, random_seed=42)
    ).generate()
    result = DockSchedulingOptimizer().optimize(bundle.inbound_trucks, bundle.dock_doors, bundle.labor_shifts)
    assert not result.dock_assignments.empty
    assert not result.labor_plan.empty
    assert {
        "recommended_dock_id",
        "recommended_reschedule_minutes",
        "estimated_congestion_risk",
        "compatibility_group",
    }.issubset(result.dock_assignments.columns)
    assert {"gap_workers", "overtime_risk", "zone_focus"}.issubset(result.labor_plan.columns)
