from fastapi import FastAPI
from app.api.routes import health, symbols, setups, backtests, alerts

app = FastAPI(
    title="LDR Scanner API",
    description="API for the Liquidity Displacement Reversal Scanner",
    version="0.1.0"
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(symbols.router, prefix="/api/v1", tags=["Symbols"])
app.include_router(setups.router, prefix="/api/v1", tags=["Setups"])
app.include_router(backtests.router, prefix="/api/v1", tags=["Backtests"])
app.include_router(alerts.router, prefix="/api/v1", tags=["Alerts"])

@app.get("/")
async def root():
    return {"message": "Welcome to the LDR Scanner API"}
