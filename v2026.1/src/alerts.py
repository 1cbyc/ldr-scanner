from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Set

import requests

from src.ldr_logic import LDRSignal

LOGGER = logging.getLogger(__name__)


class AlertState:
    def __init__(self, state_file: str):
        self.path = Path(state_file)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sent_ids: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            ids = data.get("sent_setup_ids", [])
            self.sent_ids = {str(x) for x in ids}
        except Exception as exc:
            LOGGER.warning("Could not load alert state: %s", exc)

    def _save(self) -> None:
        try:
            payload = {"sent_setup_ids": sorted(self.sent_ids)}
            self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            LOGGER.error("Could not save alert state: %s", exc)

    def is_sent(self, setup_id: str) -> bool:
        return setup_id in self.sent_ids

    def mark_sent(self, setup_id: str) -> None:
        self.sent_ids.add(setup_id)
        self._save()


class TelegramAlerter:
    def __init__(self, token: str, chat_id: str, enabled: bool = True, timeout: int = 10):
        self.enabled = enabled
        self.token = token
        self.chat_id = chat_id
        self.timeout = timeout

    def _format_message(self, signal: LDRSignal) -> str:
        direction_label = "Bearish" if signal.direction == "bearish" else "Bullish"
        bos_text = "Confirmed" if signal.bos_confirmed else "Not confirmed"
        return (
            f"🚨 {signal.symbol} {signal.timeframe} – {direction_label} LDR Detected\n\n"
            f"Sweep: {signal.sweep_price:.2f}\n"
            f"Displacement: {signal.displacement_atr:.2f} ATR\n"
            f"BOS: {bos_text}\n\n"
            f"Wait for pullback {signal.pullback_low:.2f}-{signal.pullback_high:.2f}"
        )

    def send(self, signal: LDRSignal) -> bool:
        if not self.enabled:
            LOGGER.info("Telegram disabled; signal not sent: %s", signal.setup_id)
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload: Dict[str, str] = {
            "chat_id": self.chat_id,
            "text": self._format_message(signal),
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code >= 400:
                LOGGER.error("Telegram API error %s: %s", response.status_code, response.text)
                return False
            LOGGER.info("Telegram alert sent: %s", signal.setup_id)
            return True
        except requests.RequestException as exc:
            LOGGER.error("Telegram send failed: %s", exc)
            return False
