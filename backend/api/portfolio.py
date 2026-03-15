from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from typing import List
from core.database import get_db
from core.security import get_current_user
from models.holding import Holding
from schemas.portfolio import HoldingCreate, HoldingResponse
from workers.amfi_cron import parse_and_store_navs

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


@router.post("/test-nav-refresh")
async def test_nav_refresh():
    await parse_and_store_navs()
    return {"message": "NAV refresh triggered"}


@router.post("/backfill-nav/{scheme_code}")
async def backfill_nav(scheme_code: str, db: AsyncSession = Depends(get_db)):
    import httpx
    from datetime import datetime
    from sqlalchemy import text

    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=15)

    nav_history = r.json().get("data", [])

    rows = []
    for entry in nav_history:
        try:
            date = datetime.strptime(entry["date"], "%d-%m-%Y").date()
            nav = float(entry["nav"])
            rows.append({"s": scheme_code, "d": date, "p": nav})
        except Exception:
            continue

    if rows:
        await db.execute(
            text("""
                INSERT INTO price_history (symbol, asset_type, price_date, close_price)
                VALUES (:s, 'mutualfund', :d, :p)
                ON CONFLICT (symbol, "price_date") DO NOTHING
            """),
            rows
        )
        await db.commit()

    return {"scheme_code": scheme_code, "inserted": len(rows)}
