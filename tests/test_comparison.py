from src.utils.demo import compare_named_scenarios


def test_compare_named_scenarios_returns_deltas() -> None:
    comparison = compare_named_scenarios("normal_operations", "dock_outage")
    assert not comparison.kpi_delta.empty
    assert not comparison.stage_delta.empty
    assert {"delta", "delta_pct"}.issubset(comparison.kpi_delta.columns)
    assert {"avg_minutes_delta", "bottleneck_delta"}.issubset(comparison.stage_delta.columns)
