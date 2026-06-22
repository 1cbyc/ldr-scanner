from __future__ import annotations

from typing import Optional, Tuple

import pandas as pd


def detect_swings(frame: pd.DataFrame, fractal_window: int = 5) -> pd.DataFrame:
    """Annotate DataFrame with confirmed swing highs/lows using centered fractals."""
    if fractal_window not in {3, 5}:
        raise ValueError("fractal_window must be 3 or 5")

    out = frame.copy()
    roll_high = out["high"].rolling(window=fractal_window, center=True)
    roll_low = out["low"].rolling(window=fractal_window, center=True)

    out["is_swing_high"] = out["high"].eq(roll_high.max()).fillna(False)
    out["is_swing_low"] = out["low"].eq(roll_low.min()).fillna(False)
    return out


def latest_swing_before(
    frame: pd.DataFrame,
    row_index: int,
    swing_column: str,
    price_column: str,
) -> Optional[Tuple[int, float]]:
    """Return latest confirmed swing index/price before a target row index."""
    if row_index <= 0:
        return None

    subset = frame.iloc[:row_index]
    subset = subset[subset[swing_column]]
    if subset.empty:
        return None

    swing_idx = int(subset.index[-1])
    swing_price = float(subset.iloc[-1][price_column])
    return swing_idx, swing_price
