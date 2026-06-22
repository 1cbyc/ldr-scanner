"""
send_sample_alerts.py

Sends one Telegram message per production alert template so you can see
exactly what the scanner will send when real setups are found.

Usage (from the project root with the venv active):
    python send_sample_alerts.py
"""
import asyncio
from decimal import Decimal
from datetime import datetime, timezone

from app.alerts.telegram import TelegramAlertService
from app.alerts.renderer import AlertRenderer
from app.strategy.ldr.engine import LDRSetupCandidate
from app.strategy.ldr.models import (
    DetectedRange, LiquiditySweep, Displacement,
    FairValueGap, OrderBlock, EntryZone,
)
from app.core.enums import (
    Direction, SetupStatus, SweptSide, EntryZoneSource, Timeframe,
)

NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _range(symbol, tf, high, low):
    h, l = Decimal(str(high)), Decimal(str(low))
    return DetectedRange(
        symbol=symbol,
        timeframe=tf,
        start_time=NOW,
        end_time=NOW,
        high=h,
        low=l,
        midpoint=(h + l) / 2,
        height=h - l,
        atr_at_detection=Decimal("20.0"),
        quality_score=70,
        touches_high=3,
        touches_low=3,
    )


def _sweep_bull(swept_level, sweep_low):
    return LiquiditySweep(
        direction_after_sweep=Direction.BULLISH,
        swept_side=SweptSide.SELL_SIDE,
        swept_level=Decimal(str(swept_level)),
        sweep_candle_time=NOW,
        sweep_candle_high=Decimal(str(swept_level)),
        sweep_candle_low=Decimal(str(sweep_low)),
        sweep_distance=Decimal("12.0"),
        wick_rejection_ratio=0.72,
        close_reclaimed=True,
        quality_score=25,
    )


def _sweep_bear(swept_level, sweep_high):
    return LiquiditySweep(
        direction_after_sweep=Direction.BEARISH,
        swept_side=SweptSide.BUY_SIDE,
        swept_level=Decimal(str(swept_level)),
        sweep_candle_time=NOW,
        sweep_candle_high=Decimal(str(sweep_high)),
        sweep_candle_low=Decimal(str(swept_level)),
        sweep_distance=Decimal("14.0"),
        wick_rejection_ratio=0.68,
        close_reclaimed=True,
        quality_score=22,
    )


def _displacement_bull():
    return Displacement(
        direction=Direction.BULLISH,
        start_time=NOW,
        end_time=NOW,
        impulse_candles=3,
        body_strength=0.85,
        atr_multiple=2.2,
        broke_micro_structure=True,
        created_fvg=True,
        quality_score=20,
    )


def _displacement_bear():
    return Displacement(
        direction=Direction.BEARISH,
        start_time=NOW,
        end_time=NOW,
        impulse_candles=3,
        body_strength=0.80,
        atr_multiple=2.0,
        broke_micro_structure=True,
        created_fvg=True,
        quality_score=18,
    )


def _fvg(direction, upper, lower):
    u, l = Decimal(str(upper)), Decimal(str(lower))
    return FairValueGap(
        direction=direction,
        start_time=NOW,
        end_time=NOW,
        upper=u,
        lower=l,
        midpoint=(u + l) / 2,
        size=u - l,
        filled_percent=0.0,
        quality_score=18,
    )


def _ob(direction, high, low):
    h, l = Decimal(str(high)), Decimal(str(low))
    mid = (h + l) / 2
    return OrderBlock(
        direction=direction,
        candle_time=NOW,
        high=h,
        low=l,
        open=mid,
        close=mid,
        zone_upper=h,
        zone_lower=l,
        quality_score=15,
    )


def _entry(direction, upper, lower, invalidation, target, rr):
    u, l = Decimal(str(upper)), Decimal(str(lower))
    return EntryZone(
        direction=direction,
        upper=u,
        lower=l,
        midpoint=(u + l) / 2,
        source=EntryZoneSource.OVERLAP,
        invalidation_level=Decimal(str(invalidation)),
        target_level=Decimal(str(target)),
        estimated_rr=rr,
        quality_score=25,
    )


# ---------------------------------------------------------------------------
# Sample setups - every alert type the scanner can send
# ---------------------------------------------------------------------------

def build_samples():
    return [
        # ---- XAU/USD BULLISH - Mitigation Pending ----
        # Displacement happened, entry zone exists, price not yet retraced.
        # Message: "Wait for mitigation."
        LDRSetupCandidate(
            symbol="XAU/USD",
            direction=Direction.BULLISH,
            status=SetupStatus.MITIGATION_PENDING,
            score=82,
            drange=_range("XAU/USD", Timeframe.H1, 3380, 3310),
            sweep=_sweep_bull(3310, 3296),
            displacement=_displacement_bull(),
            fvg=_fvg(Direction.BULLISH, 3330, 3318),
            order_block=_ob(Direction.BULLISH, 3328, 3315),
            entry_zone=_entry(Direction.BULLISH, 3330, 3315, 3293, 3378, 5.2),
            target_level=3378.0,
            estimated_rr=5.2,
        ),

        # ---- XAU/USD BULLISH - Entry Zone Touched ----
        # Price has retraced into the mitigation zone. Look for LTF trigger.
        LDRSetupCandidate(
            symbol="XAU/USD",
            direction=Direction.BULLISH,
            status=SetupStatus.ENTRY_ZONE_TOUCHED,
            score=91,
            drange=_range("XAU/USD", Timeframe.H1, 3380, 3310),
            sweep=_sweep_bull(3310, 3296),
            displacement=_displacement_bull(),
            fvg=_fvg(Direction.BULLISH, 3330, 3318),
            order_block=_ob(Direction.BULLISH, 3328, 3315),
            entry_zone=_entry(Direction.BULLISH, 3330, 3315, 3293, 3378, 5.2),
            target_level=3378.0,
            estimated_rr=5.2,
        ),

        # ---- XAU/USD BEARISH - Mitigation Pending ----
        LDRSetupCandidate(
            symbol="XAU/USD",
            direction=Direction.BEARISH,
            status=SetupStatus.MITIGATION_PENDING,
            score=78,
            drange=_range("XAU/USD", Timeframe.H1, 3380, 3310),
            sweep=_sweep_bear(3380, 3396),
            displacement=_displacement_bear(),
            fvg=_fvg(Direction.BEARISH, 3365, 3352),
            order_block=_ob(Direction.BEARISH, 3368, 3355),
            entry_zone=_entry(Direction.BEARISH, 3368, 3352, 3394, 3312, 4.8),
            target_level=3312.0,
            estimated_rr=4.8,
        ),

        # ---- XAU/USD BEARISH - Entry Zone Touched ----
        LDRSetupCandidate(
            symbol="XAU/USD",
            direction=Direction.BEARISH,
            status=SetupStatus.ENTRY_ZONE_TOUCHED,
            score=88,
            drange=_range("XAU/USD", Timeframe.H1, 3380, 3310),
            sweep=_sweep_bear(3380, 3396),
            displacement=_displacement_bear(),
            fvg=_fvg(Direction.BEARISH, 3365, 3352),
            order_block=_ob(Direction.BEARISH, 3368, 3355),
            entry_zone=_entry(Direction.BEARISH, 3368, 3352, 3394, 3312, 4.8),
            target_level=3312.0,
            estimated_rr=4.8,
        ),

        # ---- NDX BULLISH - Mitigation Pending ----
        LDRSetupCandidate(
            symbol="NDX",
            direction=Direction.BULLISH,
            status=SetupStatus.MITIGATION_PENDING,
            score=76,
            drange=_range("NDX", Timeframe.H1, 21800, 21400),
            sweep=_sweep_bull(21400, 21318),
            displacement=_displacement_bull(),
            fvg=_fvg(Direction.BULLISH, 21555, 21490),
            order_block=_ob(Direction.BULLISH, 21545, 21480),
            entry_zone=_entry(Direction.BULLISH, 21555, 21480, 21310, 21792, 5.8),
            target_level=21792.0,
            estimated_rr=5.8,
        ),

        # ---- NDX BEARISH - Entry Zone Touched ----
        LDRSetupCandidate(
            symbol="NDX",
            direction=Direction.BEARISH,
            status=SetupStatus.ENTRY_ZONE_TOUCHED,
            score=84,
            drange=_range("NDX", Timeframe.H1, 21800, 21400),
            sweep=_sweep_bear(21800, 21874),
            displacement=_displacement_bear(),
            fvg=_fvg(Direction.BEARISH, 21685, 21622),
            order_block=_ob(Direction.BEARISH, 21695, 21625),
            entry_zone=_entry(Direction.BEARISH, 21695, 21622, 21878, 21412, 5.0),
            target_level=21412.0,
            estimated_rr=5.0,
        ),
    ]


async def main():
    service = TelegramAlertService()
    renderer = AlertRenderer()

    samples = build_samples()
    print("Sending sample alerts to Telegram...")
    print("=" * 55)

    for i, candidate in enumerate(samples, 1):
        message = renderer.render_telegram_message(candidate)
        success = await service.send_alert(message)
        label = (
            f"{candidate.symbol} | "
            f"{candidate.direction.value.upper()} | "
            f"{candidate.status.value}"
        )
        print(f"[{i}/{len(samples)}] {label} -> {'sent' if success else 'FAILED'}")
        await asyncio.sleep(1.5)   # avoid Telegram rate limiting

    print("=" * 55)
    print(f"Done. {len(samples)} messages sent to your Telegram chat.")


if __name__ == "__main__":
    asyncio.run(main())
