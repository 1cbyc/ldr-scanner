from enum import Enum

class Timeframe(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"

class Session(str, Enum):
    ASIA = "Asia"
    LONDON = "London"
    NEW_YORK = "New York"
    LONDON_NY_OVERLAP = "London/NY Overlap"
    OTHER = "Other"

class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"

class SetupStatus(str, Enum):
    OBSERVING_RANGE = "observing_range"
    LIQUIDITY_SWEPT = "liquidity_swept"
    DISPLACEMENT_CONFIRMED = "displacement_confirmed"
    MITIGATION_PENDING = "mitigation_pending"
    ENTRY_ZONE_TOUCHED = "entry_zone_touched"
    ALERT_SENT = "alert_sent"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    COMPLETED = "completed"
    REJECTED = "rejected"

class SweptSide(str, Enum):
    BUY_SIDE = "buy_side"
    SELL_SIDE = "sell_side"

class EntryZoneSource(str, Enum):
    FVG = "fvg"
    ORDER_BLOCK = "order_block"
    OVERLAP = "overlap"
