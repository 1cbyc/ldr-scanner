from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from src.data_stream import PriceTick


@dataclass(frozen=True)
class ClosedCandleEvent:
    """Represents a newly closed candle ready for strategy evaluation."""

    instrument: str
    timeframe: str
    close_time: pd.Timestamp


class CandleBuilder:
    """Build timeframe candles from price ticks while retaining rolling history."""

    def __init__(self, instruments: List[str], timeframes: List[str], max_candles: int = 300):
        self.instruments = instruments
        self.timeframes = timeframes
        self.max_candles = max_candles
        self._history: Dict[str, Dict[str, pd.DataFrame]] = {
            instrument: {
                tf: pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
                for tf in timeframes
            }
            for instrument in instruments
        }
        self._active: Dict[str, Dict[str, Optional[Dict[str, float | pd.Timestamp | int]]]] = {
            instrument: {tf: None for tf in timeframes}
            for instrument in instruments
        }

    def seed_history(self, instrument: str, timeframe: str, frame: pd.DataFrame) -> None:
        """Seed historical candles for a symbol/timeframe pair."""
        normalized = self._normalize_frame(frame)
        self._history[instrument][timeframe] = normalized.tail(self.max_candles).reset_index(drop=True)
        self._active[instrument][timeframe] = None

    def update(self, tick: PriceTick) -> List[ClosedCandleEvent]:
        """Update active candles using a tick and return any newly closed candles."""
        events: List[ClosedCandleEvent] = []
        for timeframe in self.timeframes:
            event = self._update_timeframe(tick, timeframe)
            if event is not None:
                events.append(event)
        return events

    def get_frame(self, instrument: str, timeframe: str) -> pd.DataFrame:
        """Return a copy of closed candle history for a symbol/timeframe."""
        return self._history[instrument][timeframe].copy()

    def _normalize_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Normalize candle frame schema and sort order."""
        required = ["time", "open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in frame.columns]
        if missing:
            raise ValueError(f"Candle frame missing columns: {missing}")
        out = frame[required].copy()
        out["time"] = pd.to_datetime(out["time"], utc=True)
        return out.sort_values("time").reset_index(drop=True)

    def _update_timeframe(self, tick: PriceTick, timeframe: str) -> Optional[ClosedCandleEvent]:
        """Update a single timeframe candle state and close candles on bucket rollover."""
        instrument = tick.instrument
        bucket_start = self._bucket_start(tick.timestamp, timeframe)
        price = tick.mid
        active = self._active[instrument][timeframe]

        if active is None:
            self._active[instrument][timeframe] = {
                "time": bucket_start,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 1,
            }
            return None

        active_time = pd.Timestamp(active["time"])
        if bucket_start == active_time:
            active["high"] = max(float(active["high"]), price)
            active["low"] = min(float(active["low"]), price)
            active["close"] = price
            active["volume"] = int(active["volume"]) + 1
            return None

        closed_row = {
            "time": active_time,
            "open": float(active["open"]),
            "high": float(active["high"]),
            "low": float(active["low"]),
            "close": float(active["close"]),
            "volume": int(active["volume"]),
        }
        history = self._history[instrument][timeframe]
        history = pd.concat([history, pd.DataFrame([closed_row])], ignore_index=True)
        history = history.tail(self.max_candles).reset_index(drop=True)
        self._history[instrument][timeframe] = history

        self._active[instrument][timeframe] = {
            "time": bucket_start,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": 1,
        }

        return ClosedCandleEvent(instrument=instrument, timeframe=timeframe, close_time=active_time)

    def _bucket_start(self, ts: pd.Timestamp, timeframe: str) -> pd.Timestamp:
        """Map timestamp to timeframe bucket start using UTC alignment."""
        utc_ts = ts.tz_convert("UTC") if ts.tzinfo is not None else ts.tz_localize("UTC")
        if timeframe == "H1":
            return utc_ts.floor("1h")
        if timeframe == "H4":
            return utc_ts.floor("4h")
        raise ValueError(f"Unsupported timeframe: {timeframe}")
