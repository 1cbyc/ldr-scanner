from app.strategy.ldr.engine import LDRSetupCandidate
from app.core.enums import Direction, SetupStatus
from typing import Optional

class AlertRenderer:
    def render_telegram_message(self, candidate: LDRSetupCandidate) -> str:
        """
        Renders the LDRSetupCandidate into the required Telegram message format.
        """
        direction_str = "Bullish" if candidate.direction == Direction.BULLISH else "Bearish"
        
        # Setup Status formatting
        status_str = candidate.status.value.replace("_", " ").title()
        
        # Base Title
        message = f"🚨 *LDR SETUP DETECTED* 🚨\n\n"
        message += f"**Symbol:** {candidate.symbol}\n"
        message += f"**Direction:** {direction_str}\n"
        # We don't have session mapped here yet, so we'll just say N/A or derive it
        message += f"**Session:** N/A\n"
        message += f"**Status:** {status_str}\n"
        message += f"**Score:** {candidate.score}/100\n\n"
        
        # Range
        if candidate.drange:
            message += f"**Range:**\n"
            message += f"High: {candidate.drange.high}\n"
            message += f"Low: {candidate.drange.low}\n"
            message += f"Midpoint: {candidate.drange.midpoint}\n\n"
            
        # Sweep
        if candidate.sweep:
            swept_side = "Buy-side" if candidate.sweep.swept_side == "buy_side" else "Sell-side"
            message += f"**Liquidity Event:**\n"
            message += f"{swept_side} sweep around {candidate.sweep.swept_level}\n"
            if candidate.direction == Direction.BEARISH:
                message += f"Sweep high: {candidate.sweep.sweep_candle_high}\n"
            else:
                message += f"Sweep low: {candidate.sweep.sweep_candle_low}\n"
            message += f"Rejection confirmed: {'yes' if candidate.sweep.close_reclaimed else 'no'}\n\n"
            
        # Displacement
        if candidate.displacement:
            message += f"**Displacement:**\n"
            message += f"{direction_str} displacement confirmed\n"
            message += f"FVG created: {'yes' if candidate.fvg else 'no'}\n"
            message += f"Micro structure broken: {'yes' if candidate.displacement.broke_micro_structure else 'no'}\n\n"
            
        # Entry Zone
        if candidate.entry_zone:
            message += f"**Entry Zone:**\n"
            message += f"{candidate.entry_zone.lower} - {candidate.entry_zone.upper}\n\n"
            
            message += f"**Invalidation:**\n"
            invalid_cond = "Close above" if candidate.direction == Direction.BEARISH else "Close below"
            message += f"{invalid_cond} {candidate.entry_zone.invalidation_level}\n\n"
            
            message += f"**Target:**\n"
            message += f"{candidate.target_level} first liquidity target\n\n"
            
            if candidate.estimated_rr:
                message += f"**Estimated RR:**\n"
                message += f"1:{candidate.estimated_rr:.1f}\n\n"
                
        message += f"**Action:**\n"
        if candidate.status == SetupStatus.MITIGATION_PENDING:
            message += "Do not chase. Wait for mitigation into entry zone and m5 rejection."
        elif candidate.status == SetupStatus.ENTRY_ZONE_TOUCHED:
            message += "Price is in entry zone. Look for execution trigger on lower timeframe."
            
        return message
