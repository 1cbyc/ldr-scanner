from __future__ import annotations

import asyncio
import logging
import signal
from logging.handlers import RotatingFileHandler
from pathlib import Path

import aiohttp

from src.alerts import TelegramAlerter
from src.candle_builder import CandleBuilder
from src.config import AppConfig, load_config
from src.data_stream import OandaStreamClient
from src.scanner import LDRScanner


def setup_logging(config: AppConfig) -> None:
    """Configure console and rotating file logging for scanner runtime."""
    log_path = Path(config.logging.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(config.logging.level.upper())
    root_logger.handlers.clear()

    file_handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=5)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)


def register_signals(stop_event: asyncio.Event) -> None:
    """Attach SIGINT/SIGTERM handlers for graceful application shutdown."""
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        logging.getLogger(__name__).info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            signal.signal(sig, lambda _s, _f: stop_event.set())


async def run() -> None:
    """Initialize app components and run streaming scanner until stopped."""
    config = load_config("config/settings.yaml")
    setup_logging(config)

    timeout = aiohttp.ClientTimeout(total=config.oanda.request_timeout_sec)
    connector = aiohttp.TCPConnector(limit=100, ssl=True)

    stop_event = asyncio.Event()
    register_signals(stop_event)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        stream_client = OandaStreamClient(config.oanda, session)
        candle_builder = CandleBuilder(
            instruments=config.scanner.instruments,
            timeframes=[config.scanner.primary_timeframe, config.scanner.bias_timeframe],
            max_candles=config.strategy.history_bars,
        )
        alerter = TelegramAlerter(config.telegram, session)
        scanner = LDRScanner(config, stream_client, candle_builder, alerter)

        await scanner.run(stop_event)


def main() -> None:
    """Entrypoint wrapper that runs scanner in asyncio event loop."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
