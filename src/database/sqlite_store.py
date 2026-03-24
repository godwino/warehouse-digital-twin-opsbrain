from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, inspect


class SQLiteStore:
    """Simple dataframe persistence for local demos and repeatable workflows."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

    def save_table(self, table_name: str, frame: pd.DataFrame) -> None:
        frame.to_sql(table_name, self.engine, if_exists="replace", index=False)

    def append_table(self, table_name: str, frame: pd.DataFrame) -> None:
        frame.to_sql(table_name, self.engine, if_exists="append", index=False)

    def load_table(self, table_name: str) -> pd.DataFrame:
        if not self.table_exists(table_name):
            return pd.DataFrame()
        return pd.read_sql_table(table_name, self.engine)

    def table_exists(self, table_name: str) -> bool:
        return inspect(self.engine).has_table(table_name)
