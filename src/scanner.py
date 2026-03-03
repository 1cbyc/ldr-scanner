from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Set

import pandas as pd

from src.alerts import TelegramAlerter
from src.candle_builder import CandleBuilder, ClosedCandleEvent
from src.config import AppConfig
from src.data_stream import OandaStreamClient, PriceTick
from src.ldr_logic import LDRSignal, evaluate_primary_ldr, infer_h4_bias

LOGGER = logging.getLogger(__name__)


@dataclass
class ActiveSetup:
    """Tracks active setup lifecycle for duplicate control and invalidation."""

    signal: LDRSignal
    status: str


class LDRScanner:
    """Event-driven scanner that evaluates LDR setups from streaming price data."""

    def __init__(
        self,
        config: AppConfig,
        stream_client: OandaStreamClient,
        candle_builder: CandleBuilder,
        alerter: TelegramAlerter,
    ):
        self.config = config
        self.stream_client = stream_client
        self.candle_builder = candle_builder
        self.alerter = alerter
        self.tick_queue: asyncio.Queue[PriceTick] = asyncio.Queue(maxsize=20000)
        self.sent_setup_ids: Set[str] = set()
        self.active_setups: Dict[str, ActiveSetup] = {}

    async def bootstrap_history(self) -> None:
        """Load historical H1/H4 candles so scanner starts with valid context."""
        for instrument in self.config.scanner.instruments:
            for timeframe in [self.config.scanner.primary_timeframe, self.config.scanner.bias_timeframe]:
                frame = await self.stream_client.fetch_historical_candles(
                    instrument=instrument,
                    granularity=timeframe,
                    count=self.config.strategy.history_bars,
                )
                self.candle_builder.seed_history(instrument, timeframe, frame)
                LOGGER.info("Loaded %s %s candles: %s", instrument, timeframe, len(frame))

    async def run(self, stop_event: asyncio.Event) -> None:
        """Start streaming task and process ticks until stop event is set."""
        await self.bootstrap_history()

        stream_task = asyncio.create_task(
            self.stream_client.stream_prices(
                instruments=self.config.scanner.instruments,
                out_queue=self.tick_queue,
                stop_event=stop_event,
            )
        )

        try:
            while not stop_event.is_set():
                try:
                    tick = await asyncio.wait_for(
                        self.tick_queue.get(),
                        timeout=self.config.scanner.scan_interval_sec,
                    )
                except asyncio.TimeoutError:
                    continue

                await self._process_tick(tick)
        finally:
            stream_task.cancel()
            with contextlib_suppress(asyncio.CancelledError):
                await stream_task

    async def _process_tick(self, tick: PriceTick) -> None:
        """Update candles, evaluate setup invalidation, and scan on candle close events."""
        self._invalidate_if_needed(tick)
        events = self.candle_builder.update(tick)
        for event in events:
            if event.timeframe != self.config.scanner.primary_timeframe:
                continue
            await self._evaluate_instrument(event.instrument, event)

    async def _evaluate_instrument(self, instrument: str, event: ClosedCandleEvent) -> None:
        """Evaluate primary timeframe LDR setup under H4 directional bias filter."""
        frame_h1 = self.candle_builder.get_frame(instrument, self.config.scanner.primary_timeframe)
        frame_h4 = self.candle_builder.get_frame(instrument, self.config.scanner.bias_timeframe)

        bias = infer_h4_bias(frame_h4, fractal_window=self.config.strategy.fractal_window)
        signal = evaluate_primary_ldr(frame_h1, instrument, self.config.strategy, bias)
        if signal is None:
            return

        if signal.setup_id in self.sent_setup_ids:
            LOGGER.debug("Duplicate setup suppressed %s", signal.setup_id)
            return

        sent = await self.alerter.send_signal(signal)
        if sent:
            self.sent_setup_ids.add(signal.setup_id)
            self.active_setups[self._setup_key(signal)] = ActiveSetup(signal=signal, status="active")
            LOGGER.info(
                "Signal emitted symbol=%s direction=%s time=%s bias=%s close_time=%s",
                signal.symbol,
                signal.direction,
                signal.signal_time,
                bias,
                event.close_time.isoformat(),
            )

    def _invalidate_if_needed(self, tick: PriceTick) -> None:
        """Clear active setups when invalidation price is breached by live mid-price."""
        for key, active in list(self.active_setups.items()):
            if active.signal.symbol != tick.instrument:
                continue

            signal = active.signal
            if signal.direction == "bearish" and tick.mid > signal.invalidation_price:
                LOGGER.info("Invalidated bearish setup %s on price %.5f", signal.setup_id, tick.mid)
                self.active_setups.pop(key, None)
                continue

            if signal.direction == "bullish" and tick.mid < signal.invalidation_price:
                LOGGER.info("Invalidated bullish setup %s on price %.5f", signal.setup_id, tick.mid)
                self.active_setups.pop(key, None)

    def _setup_key(self, signal: LDRSignal) -> str:
        """Return map key used to manage active setup state."""
        return f"{signal.symbol}|{signal.timeframe}|{signal.direction}"


def contextlib_suppress(*exceptions: type[BaseException]):
    """Minimal contextmanager-compatible suppressor without external dependencies."""
    from contextlib import suppress

    return suppress(*exceptions)
