from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import AlertModel

router = APIRouter()

@router.get("/alerts")
async def list_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertModel).order_by(AlertModel.sent_at.desc()).limit(100))
    alerts = result.scalars().all()
    return alerts
