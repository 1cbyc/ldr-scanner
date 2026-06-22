from typing import List, Dict, Any
from app.strategy.ldr.engine import LDRSetupCandidate

def calculate_metrics(candidates: List[LDRSetupCandidate]) -> Dict[str, Any]:
    """
    Calculates backtesting metrics from the list of raw candidates found in replay.
    """
    # Simple deduplication by range start time
    unique_setups = {}
    for c in candidates:
        if c.drange:
            # key by start time to keep unique ranges
            key = c.drange.start_time.isoformat()
            # keep the most advanced state we found for this range
            if key not in unique_setups or c.status == "entry_zone_touched":
                unique_setups[key] = c
                
    final_setups = list(unique_setups.values())
    
    total = len(final_setups)
    if total == 0:
        return {
            "total_setups": 0,
            "average_score": 0,
            "average_rr": 0
        }
        
    avg_score = sum(c.score for c in final_setups) / total
    
    # Calculate average RR for valid setups
    valid_rr = [c.estimated_rr for c in final_setups if c.estimated_rr]
    avg_rr = sum(valid_rr) / len(valid_rr) if valid_rr else 0.0
    
    return {
        "total_setups": total,
        "average_score": avg_score,
        "average_rr": avg_rr,
        "setups": [
            {
                "symbol": c.symbol,
                "direction": c.direction.value,
                "status": c.status.value,
                "score": c.score,
                "rr": c.estimated_rr
            }
            for c in final_setups
        ]
    }
