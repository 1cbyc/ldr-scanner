from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class LDRSignal:
    symbol: str
    timeframe: str
    direction: str
    signal_time: str
    sweep_price: float
    displacement_atr: float
    bos_confirmed: bool
    pullback_low: float
    pullback_high: float
    setup_id: str


def _validate_window(fractal_window: int) -> int:
    if fractal_window not in (3, 5):
        raise ValueError("fractal_window must be either 3 or 5")
    return fractal_window


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    out = df.copy()
    prev_close = out["close"].shift(1)

    tr_components = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - prev_close).abs(),
            (out["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    out["tr"] = tr_components.max(axis=1)
    out["atr"] = out["tr"].rolling(period, min_periods=period).mean()
    return out


def add_swings(df: pd.DataFrame, fractal_window: int = 5) -> pd.DataFrame:
    out = df.copy()
    window = _validate_window(fractal_window)
    center = (window - 1) // 2

    roll_high = out["high"].rolling(window=window, center=True)
    roll_low = out["low"].rolling(window=window, center=True)

    out["is_swing_high"] = out["high"].eq(roll_high.max())
    out["is_swing_low"] = out["low"].eq(roll_low.min())

    out["is_swing_high"] = out["is_swing_high"].fillna(False)
    out["is_swing_low"] = out["is_swing_low"].fillna(False)

    # Swing is only confirmed after future candles close.
    out["swing_confirmation_shift"] = center
    return out


def _latest_swing_before(df: pd.DataFrame, idx: int, swing_col: str, price_col: str) -> Optional[Dict]:
    swings = df.loc[: idx - 1]
    swings = swings[swings[swing_col]]
    if swings.empty:
        return None
    last_idx = swings.index[-1]
    row = swings.loc[last_idx]
    return {"index": int(last_idx), "price": float(row[price_col]), "time": row["time"]}


def _close_in_bottom_quarter(row: pd.Series) -> bool:
    candle_range = float(row["high"] - row["low"])
    if candle_range <= 0:
        return False
    close_pct = float((row["close"] - row["low"]) / candle_range)
    return close_pct <= 0.25


def _close_in_top_quarter(row: pd.Series) -> bool:
    candle_range = float(row["high"] - row["low"])
    if candle_range <= 0:
        return False
    close_pct = float((row["close"] - row["low"]) / candle_range)
    return close_pct >= 0.75


def _pullback_zone(row: pd.Series, direction: str) -> Optional[Dict[str, float]]:
    body = float(abs(row["close"] - row["open"]))
    if body <= 0:
        return None

    if direction == "bearish":
        z50 = float(row["close"] + 0.50 * body)
        z75 = float(row["close"] + 0.75 * body)
        return {"low": min(z50, z75), "high": max(z50, z75)}

    z50 = float(row["close"] - 0.50 * body)
    z75 = float(row["close"] - 0.75 * body)
    return {"low": min(z50, z75), "high": max(z50, z75)}


def detect_ldr_signal(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    displacement_atr_multiplier: float = 1.5,
    fractal_window: int = 5,
    atr_period: int = 14,
) -> List[LDRSignal]:
    if len(df) < max(atr_period + 20, 80):
        return []

    work = add_atr(df, period=atr_period)
    work = add_swings(work, fractal_window=fractal_window)

    center = (fractal_window - 1) // 2
    # Exclude newest forming bar and bars that cannot have confirmed swings yet.
    end_idx = len(work) - 2 - center
    if end_idx <= atr_period:
        return []

    signals: List[LDRSignal] = []

    for idx in range(atr_period + center, end_idx + 1):
        row = work.iloc[idx]
        if pd.isna(row["atr"]):
            continue

        prev_swing_high = _latest_swing_before(work, idx, "is_swing_high", "high")
        prev_swing_low = _latest_swing_before(work, idx, "is_swing_low", "low")
        if not prev_swing_high or not prev_swing_low:
            continue

        body = float(abs(row["close"] - row["open"]))
        displacement_ok = body > displacement_atr_multiplier * float(row["atr"])
        if not displacement_ok:
            continue

        bearish_sweep = float(row["high"]) > prev_swing_high["price"]
        bullish_sweep = float(row["low"]) < prev_swing_low["price"]

        if bearish_sweep and _close_in_bottom_quarter(row):
            bos = float(row["close"]) < prev_swing_low["price"]
            if bos:
                zone = _pullback_zone(row, "bearish")
                if zone:
                    signal_time = pd.Timestamp(row["time"]).isoformat()
                    setup_id = f"{symbol}:{timeframe}:bearish:{signal_time}"
                    signals.append(
                        LDRSignal(
                            symbol=symbol,
                            timeframe=timeframe,
                            direction="bearish",
                            signal_time=signal_time,
                            sweep_price=float(row["high"]),
                            displacement_atr=body / float(row["atr"]),
                            bos_confirmed=True,
                            pullback_low=zone["low"],
                            pullback_high=zone["high"],
                            setup_id=setup_id,
                        )
                    )

        if bullish_sweep and _close_in_top_quarter(row):
            bos = float(row["close"]) > prev_swing_high["price"]
            if bos:
                zone = _pullback_zone(row, "bullish")
                if zone:
                    signal_time = pd.Timestamp(row["time"]).isoformat()
                    setup_id = f"{symbol}:{timeframe}:bullish:{signal_time}"
                    signals.append(
                        LDRSignal(
                            symbol=symbol,
                            timeframe=timeframe,
                            direction="bullish",
                            signal_time=signal_time,
                            sweep_price=float(row["low"]),
                            displacement_atr=body / float(row["atr"]),
                            bos_confirmed=True,
                            pullback_low=zone["low"],
                            pullback_high=zone["high"],
                            setup_id=setup_id,
                        )
                    )

    # Return only newest signal per direction to reduce alert noise.
    dedup: Dict[str, LDRSignal] = {}
    for s in signals:
        dedup[f"{s.symbol}:{s.timeframe}:{s.direction}"] = s
    return list(dedup.values())
