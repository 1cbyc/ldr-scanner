from __future__ import annotations

import logging
from typing import Optional

import aiohttp

from src.config import TelegramConfig
from src.ldr_logic import LDRSignal

LOGGER = logging.getLogger(__name__)


class TelegramAlerter:
    """Async Telegram notifier for scanner signal events."""

    def __init__(self, config: TelegramConfig, session: aiohttp.ClientSession):
        self.config = config
        self.session = session

    async def send_signal(self, signal: LDRSignal) -> bool:
        """Send a structured Telegram message for a confirmed LDR signal."""
        if not self.config.enabled:
            LOGGER.info("Telegram disabled; skipping signal %s", signal.setup_id)
            return False

        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.chat_id,
            "text": self._format_signal(signal),
        }

        for attempt in range(1, 4):
            try:
                timeout = aiohttp.ClientTimeout(total=self.config.request_timeout_sec)
                async with self.session.post(url, json=payload, timeout=timeout) as response:
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", "1"))
                        LOGGER.warning("Telegram rate limited; retrying in %ss", retry_after)
                        await asyncio_sleep(retry_after)
                        continue
                    if response.status >= 400:
                        text = await response.text()
                        LOGGER.error("Telegram API error [%s]: %s", response.status, text)
                        return False
                    LOGGER.info("Telegram alert sent for setup %s", signal.setup_id)
                    return True
            except aiohttp.ClientError as exc:
                LOGGER.warning("Telegram request attempt %s failed: %s", attempt, exc)
                await asyncio_sleep(attempt)

        return False

    def _format_signal(self, signal: LDRSignal) -> str:
        """Render signal details in portfolio-ready operator message format."""
        direction = "Bearish" if signal.direction == "bearish" else "Bullish"
        return (
            f"🚨 {signal.symbol} {signal.timeframe} {direction} LDR Detected\n"
            f"Sweep: {signal.sweep_price:.2f}\n"
            f"Displacement: {signal.displacement_atr:.2f} ATR\n"
            f"BOS: Confirmed\n"
            f"Pullback Zone: {signal.pullback_low:.2f} – {signal.pullback_high:.2f}"
        )


async def asyncio_sleep(seconds: int) -> None:
    """Local awaitable sleep wrapper to keep alert module testable and explicit."""
    import asyncio

    await asyncio.sleep(seconds)
