from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass(frozen=True)
class OandaConfig:
    """Runtime configuration for OANDA connectivity."""

    api_key: str
    account_id: str
    environment: str
    request_timeout_sec: int
    reconnect_delay_sec: int
    max_reconnect_delay_sec: int


@dataclass(frozen=True)
class TelegramConfig:
    """Runtime configuration for Telegram alert delivery."""

    enabled: bool
    bot_token: str
    chat_id: str
    request_timeout_sec: int


@dataclass(frozen=True)
class StrategyConfig:
    """Runtime configuration for LDR strategy logic."""

    atr_period: int
    atr_multiplier: float
    fractal_window: int
    range_avg_period: int
    history_bars: int


@dataclass(frozen=True)
class ScannerConfig:
    """Runtime configuration for scanner orchestration."""

    instruments: List[str]
    primary_timeframe: str
    bias_timeframe: str
    scan_interval_sec: int


@dataclass(frozen=True)
class LoggingConfig:
    """Runtime configuration for file and console logging."""

    level: str
    file: str


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""

    oanda: OandaConfig
    telegram: TelegramConfig
    strategy: StrategyConfig
    scanner: ScannerConfig
    logging: LoggingConfig


class ConfigError(ValueError):
    """Raised when mandatory application settings are missing or invalid."""


def _read_yaml(path: Path) -> Dict[str, Any]:
    """Read a YAML file and return a dictionary payload."""
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ConfigError("Settings file must contain a top-level YAML mapping")
    return payload


def _get_required(value: str, field_name: str) -> str:
    """Validate required string settings and return trimmed value."""
    if not value or not str(value).strip():
        raise ConfigError(f"Missing required setting: {field_name}")
    return str(value).strip()


def _apply_env_overrides(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Overlay secret and deploy-specific values from environment variables."""
    oanda = raw.setdefault("oanda", {})
    telegram = raw.setdefault("telegram", {})

    env_map = {
        "OANDA_API_KEY": (oanda, "api_key"),
        "OANDA_ACCOUNT_ID": (oanda, "account_id"),
        "OANDA_ENVIRONMENT": (oanda, "environment"),
        "TELEGRAM_BOT_TOKEN": (telegram, "bot_token"),
        "TELEGRAM_CHAT_ID": (telegram, "chat_id"),
    }

    for env_name, (target, key) in env_map.items():
        value = os.getenv(env_name)
        if value is not None and value.strip() != "":
            target[key] = value

    return raw


def load_config(path: str = "config/settings.yaml") -> AppConfig:
    """Load and validate application settings from YAML and environment."""
    raw = _apply_env_overrides(_read_yaml(Path(path)))

    oanda_raw = raw.get("oanda", {})
    telegram_raw = raw.get("telegram", {})
    strategy_raw = raw.get("strategy", {})
    scanner_raw = raw.get("scanner", {})
    logging_raw = raw.get("logging", {})

    oanda = OandaConfig(
        api_key=_get_required(str(oanda_raw.get("api_key", "")), "oanda.api_key or OANDA_API_KEY"),
        account_id=_get_required(
            str(oanda_raw.get("account_id", "")),
            "oanda.account_id or OANDA_ACCOUNT_ID",
        ),
        environment=str(oanda_raw.get("environment", "practice")).strip().lower(),
        request_timeout_sec=int(oanda_raw.get("request_timeout_sec", 20)),
        reconnect_delay_sec=int(oanda_raw.get("reconnect_delay_sec", 3)),
        max_reconnect_delay_sec=int(oanda_raw.get("max_reconnect_delay_sec", 60)),
    )

    if oanda.environment not in {"practice", "live"}:
        raise ConfigError("oanda.environment must be one of: practice, live")

    telegram = TelegramConfig(
        enabled=bool(telegram_raw.get("enabled", False)),
        bot_token=str(telegram_raw.get("bot_token", "")).strip(),
        chat_id=str(telegram_raw.get("chat_id", "")).strip(),
        request_timeout_sec=int(telegram_raw.get("request_timeout_sec", 10)),
    )

    if telegram.enabled and (not telegram.bot_token or not telegram.chat_id):
        raise ConfigError(
            "telegram.enabled is true but bot_token/chat_id are missing. "
            "Use config values or TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID"
        )

    strategy = StrategyConfig(
        atr_period=int(strategy_raw.get("atr_period", 14)),
        atr_multiplier=float(strategy_raw.get("atr_multiplier", 1.5)),
        fractal_window=int(strategy_raw.get("fractal_window", 5)),
        range_avg_period=int(strategy_raw.get("range_avg_period", 10)),
        history_bars=int(strategy_raw.get("history_bars", 300)),
    )

    if strategy.fractal_window not in {3, 5}:
        raise ConfigError("strategy.fractal_window must be 3 or 5")

    scanner = ScannerConfig(
        instruments=list(scanner_raw.get("instruments", ["EUR_USD", "GBP_USD", "XAU_USD", "NAS100_USD"])),
        primary_timeframe=str(scanner_raw.get("primary_timeframe", "H1")),
        bias_timeframe=str(scanner_raw.get("bias_timeframe", "H4")),
        scan_interval_sec=int(scanner_raw.get("scan_interval_sec", 1)),
    )

    logging_cfg = LoggingConfig(
        level=str(logging_raw.get("level", "INFO")),
        file=str(logging_raw.get("file", "logs/ldr_scanner.log")),
    )

    return AppConfig(
        oanda=oanda,
        telegram=telegram,
        strategy=strategy,
        scanner=scanner,
        logging=logging_cfg,
    )
