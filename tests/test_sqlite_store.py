from pathlib import Path

import pandas as pd

from src.database.sqlite_store import SQLiteStore


def test_sqlite_store_append_and_load(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite"
    store = SQLiteStore(db_path)
    first = pd.DataFrame([{"run_id": "1", "scenario_name": "normal_operations"}])
    second = pd.DataFrame([{"run_id": "2", "scenario_name": "dock_outage"}])

    store.append_table("scenario_runs", first)
    store.append_table("scenario_runs", second)
    loaded = store.load_table("scenario_runs")

    assert len(loaded) == 2
    assert set(loaded["scenario_name"]) == {"normal_operations", "dock_outage"}
