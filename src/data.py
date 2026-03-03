from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import MetaTrader5 as mt5
import pandas as pd

LOGGER = logging.getLogger(__name__)

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


@dataclass
class MT5Config:
    path: Optional[str]
    login: Optional[int]
    password: Optional[str]
    server: Optional[str]
    timeout_ms: int = 60000


class MT5Client:
    def __init__(self, config: MT5Config):
        self.config = config
        self._connected = False

    def connect(self) -> None:
        kwargs = {}
        if self.config.path:
            kwargs["path"] = self.config.path
        if self.config.login is not None:
            kwargs["login"] = self.config.login
            kwargs["password"] = self.config.password
            kwargs["server"] = self.config.server
            kwargs["timeout"] = self.config.timeout_ms

        if not mt5.initialize(**kwargs):
            code, message = mt5.last_error()
            raise RuntimeError(f"MT5 initialize failed: {code} {message}")

        self._connected = True
        LOGGER.info("MT5 connection initialized")

    def shutdown(self) -> None:
        if self._connected:
            mt5.shutdown()
            self._connected = False
            LOGGER.info("MT5 connection closed")

    def ensure_symbol(self, symbol: str) -> None:
        info = mt5.symbol_info(symbol)
        if info is None:
            raise ValueError(f"Symbol not available in MT5 terminal: {symbol}")
        if not info.visible and not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Failed to select symbol: {symbol}")

    def get_rates(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        if timeframe not in TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        self.ensure_symbol(symbol)
        mt5_tf = TIMEFRAME_MAP[timeframe]
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, bars)
        if rates is None:
            code, message = mt5.last_error()
            raise RuntimeError(f"MT5 copy_rates_from_pos failed [{symbol} {timeframe}]: {code} {message}")

        df = pd.DataFrame(rates)
        if df.empty:
            raise RuntimeError(f"No rates returned for {symbol} {timeframe}")

        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.rename(
            columns={
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "tick_volume": "volume",
            }
        )
        return df[["time", "open", "high", "low", "close", "volume"]].copy()


def build_mt5_config(raw_cfg: Dict) -> MT5Config:
    mt5_cfg = raw_cfg.get("mt5", {})
    login = mt5_cfg.get("login")
    return MT5Config(
        path=mt5_cfg.get("path"),
        login=int(login) if login is not None else None,
        password=mt5_cfg.get("password"),
        server=mt5_cfg.get("server"),
        timeout_ms=int(mt5_cfg.get("timeout_ms", 60000)),
    )
