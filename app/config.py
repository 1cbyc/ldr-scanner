from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    DATABASE_URL: str = ""
    REDIS_URL: str = ""

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

    # Invalidation buffer added to the sweep level when computing the stop price.
    # This is a raw price unit value (e.g. 0.5 = half a point on Gold).
    # Set it to a meaningful value for each instrument via the .env file.
    INVALIDATION_ATR_BUFFER: float = 0.5

    # Fraction of ATR that a counter-move candle body must exceed before it
    # is considered a displacement failure and scanning stops early.
    DISPLACEMENT_REJECTION_ATR_FRACTION: float = 0.5

    # Scoring constants for the entry zone detector.
    ENTRY_ZONE_OVERLAP_SCORE: int = 15
    ENTRY_ZONE_BASE_SCORE: int = 10

    # Scoring constant for the order block detector.
    ORDER_BLOCK_BASE_SCORE: int = 15

    # Number of candles fetched per symbol/timeframe in each live scan cycle.
    SCANNER_CANDLE_LIMIT: int = 200

    # Maximum candles to load when running a backtest from CSV.
    BACKTEST_CANDLE_LIMIT: int = 5000

    # Mock provider base prices per symbol, comma-separated.
    # Format: "XAUUSD:4300,NAS100:15000,EURUSD:1.09"
    MOCK_BASE_PRICES: str = "XAUUSD:4300,NAS100:15000,EURUSD:1.09"

    @property
    def symbols_list(self) -> List[str]:
        return [s.strip() for s in self.SYMBOLS.split(",") if s.strip()]

    @property
    def timeframes_list(self) -> List[str]:
        return [t.strip() for t in self.DEFAULT_TIMEFRAMES.split(",") if t.strip()]

settings = Settings()
