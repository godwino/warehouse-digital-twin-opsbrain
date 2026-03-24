from __future__ import annotations

from pathlib import Path

from src.config.settings import ScenarioConfig, get_settings
from src.data.generator import SyntheticWarehouseDataGenerator, WarehouseDataBundle
from src.database.sqlite_store import SQLiteStore
from src.utils.io import save_frames_to_csv


def build_synthetic_dataset(
    scenario: ScenarioConfig | None = None, output_dir: Path | None = None
) -> WarehouseDataBundle:
    settings = get_settings()
    scenario = scenario or settings.default_scenario
    output_dir = output_dir or settings.data_dir / scenario.name
    generator = SyntheticWarehouseDataGenerator(config=scenario)
    bundle = generator.generate()

    store = SQLiteStore(settings.db_path)
    for table_name, frame in bundle.to_dict().items():
        store.save_table(table_name, frame)

    save_frames_to_csv(bundle.to_dict(), output_dir)
    return bundle
