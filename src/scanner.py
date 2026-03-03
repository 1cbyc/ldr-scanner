from __future__ import annotations

import logging
import time
from typing import Dict, List

from src.alerts import AlertState, TelegramAlerter
from src.data import MT5Client
from src.ldr_logic import LDRSignal, detect_ldr_signal

LOGGER = logging.getLogger(__name__)


class LDRScanner:
    def __init__(
        self,
        mt5_client: MT5Client,
        alerter: TelegramAlerter,
        alert_state: AlertState,
        config: Dict,
    ):
        self.mt5_client = mt5_client
        self.alerter = alerter
        self.alert_state = alert_state

        self.symbols: List[str] = list(config["scanner"]["symbols"])
        self.timeframes: List[str] = list(config["scanner"]["timeframes"])
        self.bars: int = int(config["scanner"].get("bars", 500))
        self.scan_interval_sec: int = int(config["scanner"].get("scan_interval_sec", 30))

        self.fractal_window: int = int(config["strategy"].get("fractal_window", 5))
        self.atr_period: int = int(config["strategy"].get("atr_period", 14))
        self.displacement_atr_multiplier: float = float(
            config["strategy"].get("displacement_atr_multiplier", 1.5)
        )

    def run_forever(self) -> None:
        self.mt5_client.connect()
        LOGGER.info("LDR scanner started")

        try:
            while True:
                self.scan_once()
                time.sleep(self.scan_interval_sec)
        finally:
            self.mt5_client.shutdown()

    def scan_once(self) -> None:
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                try:
                    df = self.mt5_client.get_rates(symbol, timeframe, self.bars)
                    signals = detect_ldr_signal(
                        df=df,
                        symbol=symbol,
                        timeframe=timeframe,
                        displacement_atr_multiplier=self.displacement_atr_multiplier,
                        fractal_window=self.fractal_window,
                        atr_period=self.atr_period,
                    )
                    self._process_signals(signals)
                except Exception as exc:
                    LOGGER.exception("Scan failed for %s %s: %s", symbol, timeframe, exc)

    def _process_signals(self, signals: List[LDRSignal]) -> None:
        for signal in signals:
            if self.alert_state.is_sent(signal.setup_id):
                LOGGER.debug("Duplicate skipped: %s", signal.setup_id)
                continue

            sent = self.alerter.send(signal)
            if sent:
                self.alert_state.mark_sent(signal.setup_id)
                LOGGER.info(
                    "LDR signal emitted %s %s %s at %s",
                    signal.symbol,
                    signal.timeframe,
                    signal.direction,
                    signal.signal_time,
                )
