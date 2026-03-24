from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.ui import render_download, render_page_hero, render_stat_cards
from src.config.settings import ScenarioConfig
from src.utils.demo import run_mvp_pipeline

artifacts = run_mvp_pipeline(ScenarioConfig())
render_page_hero(
    "Data Explorer",
    "Browse the synthetic warehouse entities and events that feed the forecasts, optimizers, simulation, and recommendations."
)
selected = st.selectbox("Dataset", list(artifacts.dataset.keys()))
frame = artifacts.dataset[selected]
numeric_columns = frame.select_dtypes(include="number").columns
render_stat_cards(
    [
        ("Dataset", selected, "Currently selected source table."),
        ("Rows", f"{len(frame):,}", "Record count."),
        ("Columns", f"{len(frame.columns)}", "Available fields."),
        (
            "Numeric Fields",
            f"{len(numeric_columns)}",
            "Columns available for quick quantitative profiling.",
        ),
    ]
)
if len(numeric_columns) > 0:
    stats = frame[numeric_columns].describe().transpose().reset_index().rename(columns={"index": "column"})
else:
    stats = pd.DataFrame(columns=["column", "count", "mean", "std", "min", "25%", "50%", "75%", "max"])

left, right = st.columns([1.8, 1.2])
with left:
    st.dataframe(frame, use_container_width=True, hide_index=True)
with right:
    st.subheader("Numeric Profile")
    st.dataframe(stats, use_container_width=True, hide_index=True)

render_download(frame, "Download selected dataset", f"{selected}.csv")
