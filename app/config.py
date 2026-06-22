from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/ldr_scanner"
    REDIS_URL: str = "redis://localhost:6379/0"

    DATA_PROVIDER: str = "csv"
    TWELVEDATA_API_KEY: str = ""
    CSV_DATA_DIR: str = "./data/csv"

    SYMBOLS: str = "XAUUSD,NAS100,EURUSD"
    DEFAULT_TIMEFRAMES: str = "H1,M15,M5"

    USER_TIMEZONE: str = "Africa/Lagos"

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    MIN_RR: float = 5.0
    ALERT_SCORE_THRESHOLD: int = 75
    SCAN_INTERVAL_SECONDS: int = 60

    RANGE_MIN_CANDLES: int = 12
    RANGE_MAX_CANDLES: int = 60
    SWEEP_MAX_ATR_MULTIPLE: float = 1.5
    DISPLACEMENT_MIN_ATR_MULTIPLE: float = 1.2
    SETUP_EXPIRY_CANDLES: int = 24

    @property
    def symbols_list(self) -> List[str]:
        return [s.strip() for s in self.SYMBOLS.split(",") if s.strip()]

    @property
    def timeframes_list(self) -> List[str]:
        return [t.strip() for t in self.DEFAULT_TIMEFRAMES.split(",") if t.strip()]

settings = Settings()
