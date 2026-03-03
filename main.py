from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

import yaml

from src.alerts import AlertState, TelegramAlerter
from src.data import MT5Client, build_mt5_config
from src.scanner import LDRScanner


def setup_logging(log_file: str, level: str = "INFO") -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(level.upper())

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5)
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)

    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if not isinstance(cfg, dict):
        raise ValueError("Config YAML must be a dictionary")

    required_top_keys = ["mt5", "scanner", "strategy", "telegram", "logging"]
    missing = [k for k in required_top_keys if k not in cfg]
    if missing:
        raise ValueError(f"Missing top-level config keys: {missing}")

    return cfg


def apply_env_overrides(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Override sensitive config values from environment variables."""
    mt5_cfg = cfg.setdefault("mt5", {})
    telegram_cfg = cfg.setdefault("telegram", {})

    env_map = (
        ("MT5_PATH", mt5_cfg, "path"),
        ("MT5_LOGIN", mt5_cfg, "login"),
        ("MT5_PASSWORD", mt5_cfg, "password"),
        ("MT5_SERVER", mt5_cfg, "server"),
        ("TELEGRAM_BOT_TOKEN", telegram_cfg, "token"),
        ("TELEGRAM_CHAT_ID", telegram_cfg, "chat_id"),
    )

    for env_name, target_cfg, key in env_map:
        value = os.getenv(env_name)
        if value is not None and value.strip() != "":
            target_cfg[key] = value

    return cfg


def main() -> None:
    cfg = apply_env_overrides(load_config("config/settings.yaml"))
    setup_logging(
        log_file=str(cfg["logging"].get("file", "logs/ldr_scanner.log")),
        level=str(cfg["logging"].get("level", "INFO")),
    )

    alert_state = AlertState(state_file=str(cfg["logging"].get("state_file", "logs/alert_state.json")))

    telegram_cfg = cfg["telegram"]
    alerter = TelegramAlerter(
        token=str(telegram_cfg.get("token", "")),
        chat_id=str(telegram_cfg.get("chat_id", "")),
        enabled=bool(telegram_cfg.get("enabled", False)),
        timeout=int(telegram_cfg.get("timeout_sec", 10)),
    )

    mt5_client = MT5Client(build_mt5_config(cfg))
    scanner = LDRScanner(
        mt5_client=mt5_client,
        alerter=alerter,
        alert_state=alert_state,
        config=cfg,
    )
    scanner.run_forever()


if __name__ == "__main__":
    main()
