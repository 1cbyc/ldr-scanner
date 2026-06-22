from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from app.db.session import get_db
from app.db.models import LDRSetupModel

router = APIRouter()

@router.get("/setups")
async def list_setups(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    min_score: int = 0,
    db: AsyncSession = Depends(get_db)
):
    query = select(LDRSetupModel)
    if symbol:
        query = query.filter(LDRSetupModel.symbol == symbol)
    if status:
        query = query.filter(LDRSetupModel.status == status)
    if min_score > 0:
        query = query.filter(LDRSetupModel.score >= min_score)
        
    result = await db.execute(query)
    setups = result.scalars().all()
    
    return setups

@router.get("/setups/{setup_id}")
async def get_setup(setup_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LDRSetupModel).filter(LDRSetupModel.id == setup_id))
    setup = result.scalar_one_or_none()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")
    return setup
