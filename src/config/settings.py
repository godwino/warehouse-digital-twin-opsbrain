from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScenarioConfig(BaseModel):
    name: Literal[
        "normal_operations",
        "peak_season",
        "labor_shortage",
        "dock_outage",
        "surge_inbound_day",
        "fragile_load_mix_increase",
    ] = "normal_operations"
    horizon_days: int = Field(default=90, ge=14, le=365)
    random_seed: int = 42
    inbound_volume_multiplier: float = Field(default=1.0, ge=0.5, le=3.0)
    active_dock_ratio: float = Field(default=1.0, ge=0.2, le=1.0)
    labor_availability_ratio: float = Field(default=1.0, ge=0.3, le=1.2)
    fragile_mix_delta: float = Field(default=0.0, ge=0.0, le=0.5)
    priority_mix_delta: float = Field(default=0.0, ge=0.0, le=0.4)
    operating_hours: int = Field(default=18, ge=8, le=24)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HVDC_", env_file=".env", extra="ignore")

    app_name: str = "HVDC OpsBrain"
    base_dir: Path = Path(__file__).resolve().parents[2]
    outputs_dir: Path = base_dir / "outputs"
    data_dir: Path = outputs_dir / "data"
    models_dir: Path = outputs_dir / "models"
    reports_dir: Path = outputs_dir / "reports"
    db_path: Path = data_dir / "opsbrain.sqlite"
    default_scenario: ScenarioConfig = ScenarioConfig()


def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return settings


def build_named_scenario(name: str) -> ScenarioConfig:
    presets: dict[str, dict[str, float | int | str]] = {
        "normal_operations": {"name": "normal_operations"},
        "peak_season": {
            "name": "peak_season",
            "inbound_volume_multiplier": 1.2,
            "priority_mix_delta": 0.04,
        },
        "labor_shortage": {
            "name": "labor_shortage",
            "labor_availability_ratio": 0.72,
        },
        "dock_outage": {
            "name": "dock_outage",
            "active_dock_ratio": 0.75,
        },
        "surge_inbound_day": {
            "name": "surge_inbound_day",
            "inbound_volume_multiplier": 1.45,
        },
        "fragile_load_mix_increase": {
            "name": "fragile_load_mix_increase",
            "fragile_mix_delta": 0.2,
        },
    }
    return ScenarioConfig(**presets.get(name, {"name": "normal_operations"}))
