from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from core.database import get_db
from core.security import get_current_user
from models.holding import Holding
from schemas.portfolio import HoldingCreate, HoldingResponse

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])

@router.get("", response_model=List[HoldingResponse])
async def get_portfolio(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Holding).where(Holding.user_id == user["sub"])
    )
    return result.scalars().all()

@router.post("", response_model=HoldingResponse)
async def add_holding(
    item: HoldingCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    holding = Holding(**item.model_dump(), user_id=user["sub"])
    db.add(holding)
    await db.commit()
    await db.refresh(holding)
    return holding

@router.delete("/{holding_id}")
async def remove_holding(
    holding_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        delete(Holding).where(
            Holding.id == holding_id,
            Holding.user_id == user["sub"]
        )
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"message": "Removed"}
