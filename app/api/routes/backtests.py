from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
from app.backtesting.runner import BacktestRunner
from app.data.providers.csv_provider import CSVProvider
from app.core.enums import Timeframe

router = APIRouter()

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: Timeframe

@router.post("/backtests")
async def create_backtest(req: BacktestRequest):
    # In V1 we run synchronously and return the result right away
    provider = CSVProvider()
    runner = BacktestRunner(provider)
    metrics = await runner.run_backtest(req.symbol, req.timeframe)
    return metrics

@router.get("/backtests/{run_id}")
async def get_backtest(run_id: int):
    return {"status": "Not implemented. Backtests run synchronously in V1."}
