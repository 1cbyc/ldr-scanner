from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.config import StrategyConfig
from src.indicators import add_atr, add_range_stats
from src.structure import detect_swings, latest_swing_before


@dataclass(frozen=True)
class LDRSignal:
    """Represents a fully confirmed LDR setup."""

    symbol: str
    timeframe: str
    direction: str
    signal_time: str
    sweep_price: float
    displacement_atr: float
    bos_confirmed: bool
    pullback_low: float
    pullback_high: float
    invalidation_price: float
    setup_id: str


def infer_h4_bias(frame_h4: pd.DataFrame, fractal_window: int) -> str:
    """Infer directional bias from latest H4 close against confirmed swing structure."""
    if frame_h4.empty or len(frame_h4) < fractal_window + 10:
        return "neutral"

    work = detect_swings(frame_h4, fractal_window=fractal_window)
    idx = len(work) - 1

    recent_high = latest_swing_before(work, idx, "is_swing_high", "high")
    recent_low = latest_swing_before(work, idx, "is_swing_low", "low")
    if not recent_high or not recent_low:
        return "neutral"

    close = float(work.iloc[idx]["close"])
    if close > recent_high[1]:
        return "bullish"
    if close < recent_low[1]:
        return "bearish"
    return "neutral"


def evaluate_primary_ldr(
    frame_h1: pd.DataFrame,
    symbol: str,
    strategy: StrategyConfig,
    bias: str,
) -> Optional[LDRSignal]:
    """Evaluate most recent closed H1 candle for a complete mechanical LDR setup."""
    minimum = max(strategy.atr_period + 20, strategy.history_bars // 3)
    if len(frame_h1) < minimum:
        return None

    work = add_atr(frame_h1, period=strategy.atr_period)
    work = add_range_stats(work, avg_period=strategy.range_avg_period)
    work = detect_swings(work, fractal_window=strategy.fractal_window)

    idx = len(work) - 1
    row = work.iloc[idx]

    if pd.isna(row["atr"]) or pd.isna(row["avg_range"]):
        return None

    swing_high = latest_swing_before(work, idx, "is_swing_high", "high")
    swing_low = latest_swing_before(work, idx, "is_swing_low", "low")
    if not swing_high or not swing_low:
        return None

    body = abs(float(row["close"]) - float(row["open"]))
    candle_range = float(row["high"] - row["low"])
    if candle_range <= 0:
        return None

    atr = float(row["atr"])
    avg_range = float(row["avg_range"])
    if atr <= 0 or avg_range <= 0:
        return None

    displacement_ok = body > strategy.atr_multiplier * atr
    range_expansion_ok = candle_range > avg_range
    close_pct = (float(row["close"]) - float(row["low"])) / candle_range

    bearish_sweep = float(row["high"]) > swing_high[1]
    bearish_close_ok = close_pct <= 0.25
    bearish_bos = float(row["close"]) < swing_low[1]

    bullish_sweep = float(row["low"]) < swing_low[1]
    bullish_close_ok = close_pct >= 0.75
    bullish_bos = float(row["close"]) > swing_high[1]

    signal_time = pd.Timestamp(row["time"]).isoformat()

    if displacement_ok and range_expansion_ok and bearish_sweep and bearish_close_ok and bearish_bos:
        if bias != "bearish":
            return None
        pullback_low, pullback_high = _pullback_zone(row, "bearish")
        ratio = body / atr
        setup_id = _setup_id(symbol, "H1", "bearish", signal_time)
        return LDRSignal(
            symbol=symbol,
            timeframe="H1",
            direction="bearish",
            signal_time=signal_time,
            sweep_price=float(row["high"]),
            displacement_atr=ratio,
            bos_confirmed=True,
            pullback_low=pullback_low,
            pullback_high=pullback_high,
            invalidation_price=float(row["high"]),
            setup_id=setup_id,
        )

    if displacement_ok and range_expansion_ok and bullish_sweep and bullish_close_ok and bullish_bos:
        if bias != "bullish":
            return None
        pullback_low, pullback_high = _pullback_zone(row, "bullish")
        ratio = body / atr
        setup_id = _setup_id(symbol, "H1", "bullish", signal_time)
        return LDRSignal(
            symbol=symbol,
            timeframe="H1",
            direction="bullish",
            signal_time=signal_time,
            sweep_price=float(row["low"]),
            displacement_atr=ratio,
            bos_confirmed=True,
            pullback_low=pullback_low,
            pullback_high=pullback_high,
            invalidation_price=float(row["low"]),
            setup_id=setup_id,
        )

    return None


def _pullback_zone(row: pd.Series, direction: str) -> tuple[float, float]:
    """Compute 50-75% retracement pullback zone from displacement candle body."""
    body = abs(float(row["close"]) - float(row["open"]))
    if direction == "bearish":
        zone_50 = float(row["close"]) + 0.50 * body
        zone_75 = float(row["close"]) + 0.75 * body
        return min(zone_50, zone_75), max(zone_50, zone_75)

    zone_50 = float(row["close"]) - 0.50 * body
    zone_75 = float(row["close"]) - 0.75 * body
    return min(zone_50, zone_75), max(zone_50, zone_75)


def _setup_id(symbol: str, timeframe: str, direction: str, signal_time: str) -> str:
    """Create a deterministic setup hash for duplicate-alert suppression."""
    base = f"{symbol}|{timeframe}|{direction}|{signal_time}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]
