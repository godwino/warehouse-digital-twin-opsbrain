from src.config.settings import ScenarioConfig
from src.data.generator import SyntheticWarehouseDataGenerator
from src.forecasting.engine import ForecastingEngine


def test_forecasting_outputs_expected_artifacts() -> None:
    bundle = SyntheticWarehouseDataGenerator(
        ScenarioConfig(name="normal_operations", horizon_days=45, random_seed=42)
    ).generate()
    artifacts = ForecastingEngine().fit_predict(bundle.historical_kpis, bundle.inbound_trucks)

    assert not artifacts.daily_forecast.empty
    assert not artifacts.evaluation.empty
    assert {"model", "mae", "rmse", "mape"}.issubset(artifacts.evaluation.columns)
