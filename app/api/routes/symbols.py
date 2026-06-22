from fastapi import APIRouter
from app.config import settings
from pydantic import BaseModel
from typing import List

router = APIRouter()

class SymbolResponse(BaseModel):
    symbols: List[str]
    timeframes: List[str]

@router.get("/symbols", response_model=SymbolResponse)
async def get_symbols():
    return {
        "symbols": settings.symbols_list,
        "timeframes": settings.timeframes_list
    }

@router.post("/symbols")
async def add_symbol(symbol: str):
    # In V1, configuration is in .env, so we just mock this.
    return {"status": "Not implemented. Please update .env SYMBOLS"}
