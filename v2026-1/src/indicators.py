from __future__ import annotations

import pandas as pd


def add_true_range(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute true range values and append `tr` column."""
    out = frame.copy()
    prev_close = out["close"].shift(1)
    components = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - prev_close).abs(),
            (out["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    out["tr"] = components.max(axis=1)
    return out


def add_atr(frame: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Compute simple moving ATR and append `atr` column."""
    out = add_true_range(frame)
    out["atr"] = out["tr"].rolling(window=period, min_periods=period).mean()
    return out


def add_range_stats(frame: pd.DataFrame, avg_period: int = 10) -> pd.DataFrame:
    """Append per-candle range and rolling average range columns."""
    out = frame.copy()
    out["candle_range"] = out["high"] - out["low"]
    out["avg_range"] = out["candle_range"].rolling(window=avg_period, min_periods=avg_period).mean()
    return out
