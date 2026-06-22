from fastapi import FastAPI
from app.api.routes import health

app = FastAPI(
    title="LDR Scanner API",
    description="API for the Liquidity Displacement Reversal Scanner",
    version="0.1.0"
)

app.include_router(health.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to the LDR Scanner API"}
