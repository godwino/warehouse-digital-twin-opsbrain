from __future__ import annotations

import numpy as np


def mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denominator = np.where(y_true == 0, 1, y_true)
    return float(np.mean(np.abs((y_true - y_pred) / denominator)) * 100)
