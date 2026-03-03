from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
import pandas as pd

from src.config import OandaConfig

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceTick:
    """Normalized tick payload derived from OANDA price stream events."""

    instrument: str
    timestamp: pd.Timestamp
    bid: float
    ask: float

    @property
    def mid(self) -> float:
        """Return the mid price computed from bid/ask."""
        return (self.bid + self.ask) / 2.0


class OandaStreamClient:
    """Client for OANDA v20 streaming and historical candle endpoints."""

    def __init__(self, config: OandaConfig, session: aiohttp.ClientSession):
        self.config = config
        self.session = session
        self._reconnect_delay = self.config.reconnect_delay_sec

    @property
    def _rest_base(self) -> str:
        """Return REST base URL for the selected OANDA environment."""
        if self.config.environment == "live":
            return "https://api-fxtrade.oanda.com"
        return "https://api-fxpractice.oanda.com"

    @property
    def _stream_base(self) -> str:
        """Return streaming base URL for the selected OANDA environment."""
        if self.config.environment == "live":
            return "https://stream-fxtrade.oanda.com"
        return "https://stream-fxpractice.oanda.com"

    @property
    def _headers(self) -> Dict[str, str]:
        """Return authenticated HTTP headers for OANDA API requests."""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    async def fetch_historical_candles(
        self,
        instrument: str,
        granularity: str,
        count: int,
    ) -> pd.DataFrame:
        """Fetch closed midpoint candles and return normalized OHLCV DataFrame."""
        url = f"{self._rest_base}/v3/instruments/{instrument}/candles"
        params = {
            "price": "M",
            "granularity": granularity,
            "count": str(count),
            "includeFirst": "false",
        }

        for attempt in range(1, 6):
            try:
                async with self.session.get(url, headers=self._headers, params=params) as response:
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", "1"))
                        LOGGER.warning(
                            "Rate limit hit fetching %s %s; retrying in %ss",
                            instrument,
                            granularity,
                            retry_after,
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    if response.status >= 400:
                        text = await response.text()
                        raise RuntimeError(
                            f"Historical candle request failed [{response.status}] {instrument} {granularity}: {text}"
                        )

                    payload: Dict[str, Any] = await response.json()
                    candles: List[Dict[str, Any]] = payload.get("candles", [])
                    rows: List[Dict[str, Any]] = []
                    for candle in candles:
                        if not candle.get("complete", False):
                            continue
                        mid = candle.get("mid", {})
                        rows.append(
                            {
                                "time": pd.Timestamp(candle["time"]),
                                "open": float(mid["o"]),
                                "high": float(mid["h"]),
                                "low": float(mid["l"]),
                                "close": float(mid["c"]),
                                "volume": int(candle.get("volume", 0)),
                            }
                        )

                    frame = pd.DataFrame(rows)
                    if frame.empty:
                        raise RuntimeError(f"No closed candles returned for {instrument} {granularity}")

                    frame = frame.sort_values("time").reset_index(drop=True)
                    return frame
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                LOGGER.warning(
                    "Historical fetch attempt %s failed for %s %s: %s",
                    attempt,
                    instrument,
                    granularity,
                    exc,
                )
                await asyncio.sleep(min(attempt * 2, self.config.max_reconnect_delay_sec))

        raise RuntimeError(f"Unable to fetch historical candles for {instrument} {granularity}")

    async def stream_prices(
        self,
        instruments: List[str],
        out_queue: asyncio.Queue[PriceTick],
        stop_event: asyncio.Event,
    ) -> None:
        """Maintain persistent OANDA price stream and publish ticks to queue."""
        instruments_csv = ",".join(instruments)
        url = (
            f"{self._stream_base}/v3/accounts/{self.config.account_id}/pricing/stream"
            f"?instruments={instruments_csv}"
        )

        while not stop_event.is_set():
            try:
                timeout = aiohttp.ClientTimeout(total=None, sock_read=None)
                async with self.session.get(url, headers=self._headers, timeout=timeout) as response:
                    if response.status == 401:
                        text = await response.text()
                        raise RuntimeError(f"OANDA authentication failed: {text}")
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", "1"))
                        LOGGER.warning("Streaming rate limit hit; reconnecting in %ss", retry_after)
                        await asyncio.sleep(retry_after)
                        continue
                    if response.status >= 400:
                        text = await response.text()
                        raise RuntimeError(f"Streaming connection failed [{response.status}]: {text}")

                    LOGGER.info("Connected to OANDA streaming endpoint for %s", instruments_csv)
                    self._reconnect_delay = self.config.reconnect_delay_sec
                    await self._consume_stream(response, out_queue, stop_event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOGGER.exception("Streaming error: %s", exc)
                delay = min(self._reconnect_delay, self.config.max_reconnect_delay_sec)
                LOGGER.info("Reconnecting stream in %ss", delay)
                await asyncio.sleep(delay)
                self._reconnect_delay = min(delay * 2, self.config.max_reconnect_delay_sec)

    async def _consume_stream(
        self,
        response: aiohttp.ClientResponse,
        out_queue: asyncio.Queue[PriceTick],
        stop_event: asyncio.Event,
    ) -> None:
        """Consume newline-delimited stream payload and enqueue valid price ticks."""
        async for raw_line in response.content:
            if stop_event.is_set():
                return

            line = raw_line.decode("utf-8").strip()
            if not line:
                continue

            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                LOGGER.debug("Skipping malformed stream line: %s", line)
                continue

            if payload.get("type") == "HEARTBEAT":
                continue
            if payload.get("type") != "PRICE":
                continue

            tick = self._parse_tick(payload)
            if tick is None:
                continue

            await out_queue.put(tick)

    def _parse_tick(self, payload: Dict[str, Any]) -> Optional[PriceTick]:
        """Parse OANDA PRICE payload into normalized `PriceTick` object."""
        instrument = payload.get("instrument")
        timestamp_raw = payload.get("time")
        bids = payload.get("bids") or []
        asks = payload.get("asks") or []

        if not instrument or not timestamp_raw or not bids or not asks:
            return None

        try:
            bid = float(bids[0]["price"])
            ask = float(asks[0]["price"])
            timestamp = pd.Timestamp(timestamp_raw)
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
        except (ValueError, KeyError, TypeError):
            return None

        return PriceTick(instrument=instrument, timestamp=timestamp, bid=bid, ask=ask)
