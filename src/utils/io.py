from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_frames_to_csv(frames: dict[str, pd.DataFrame], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(directory / f"{name}.csv", index=False)
