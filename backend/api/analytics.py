import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date
from core.database import get_db
from core.security import get_current_user
from core.redis import get_redis
from models.holding import Holding
from models.price_history import PriceHistory
from models.snapshot import PortfolioSnapshot
from services.analytics import calc_pnl, xirr, calc_risk_metrics, monte_carlo, numpy_to_python
from services.price_backfill import COIN_ID_TO_SYMBOL

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def _crypto_redis_key(symbol: str) -> str:
    """
    Map CoinGecko-style coin id (e.g. "ethereum") to the Binance
    Redis key written by binance_ws.py (e.g. "price:crypto:ethusdt").
    Falls back to symbol + "usdt" if not in the mapping.
    """
    sym = symbol.lower()
    binance_sym = COIN_ID_TO_SYMBOL.get(sym)
    if binance_sym:
        return f"price:crypto:{binance_sym}"
    return f"price:crypto:{sym}usdt"


REDIS_PRICE_KEYS = {
    "stock": lambda s: f"price:stock:{s.lower().replace('.', '_')}",
    "crypto": _crypto_redis_key,
    "mutualfund": lambda s: f"nav:{s}",
}

async def get_current_price(symbol: str, asset_type: str, redis) -> float | None:
    key_fn = REDIS_PRICE_KEYS.get(asset_type)
    if not key_fn:
        return None
    val = await redis.get(key_fn(symbol))
    return float(val) if val else None


async def get_price_series(symbol: str, db: AsyncSession) -> list[float]:
    result = await db.execute(
        select(PriceHistory.close_price)
        .where(PriceHistory.symbol == symbol)
        .order_by(desc(PriceHistory.price_date))
        .limit(365)
    )
    rows = result.scalars().all()
    return [float(r) for r in reversed(rows)]


@router.get("/portfolio")
async def portfolio_analytics(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()

    result = await db.execute(
        select(Holding).where(Holding.user_id == user["sub"])
    )
    holdings = result.scalars().all()

    total_invested = 0
    total_current = 0
    holdings_data = []

    for h in holdings:
        current_price = await get_current_price(h.symbol, h.asset_type, redis)
        buy_price = float(h.buy_price)
        quantity = float(h.quantity)
        if current_price is None:
            current_price = buy_price

        pnl = calc_pnl(buy_price, current_price, quantity)

        buy_date = h.buy_date if isinstance(h.buy_date, date) else date.fromisoformat(str(h.buy_date))
        cf = [(buy_date, -(buy_price * quantity)), (date.today(), pnl["current_value"])]
        holding_xirr = xirr(cf)

        # fetch price series FIRST (before cache check)
        price_series = await get_price_series(h.symbol, db)
        if len(price_series) < 2:
            price_series = [buy_price, current_price]

        # risk metrics (always computed fresh)
        risk = calc_risk_metrics(price_series)

        # Monte Carlo (cached)
        mc_cache_key = f"mc:{h.id}"
        cached_mc = await redis.get(mc_cache_key)
        if cached_mc:
            mc = json.loads(cached_mc)
        else:
            mc = monte_carlo(pnl["current_value"], price_series)
            await redis.setex(mc_cache_key, 21600, json.dumps(mc))  # 6h cache

        total_invested += pnl["invested"]
        total_current += pnl["current_value"]

        holdings_data.append({
            "id": str(h.id),
            "symbol": h.symbol,
            "name": h.name,
            "asset_type": h.asset_type,
            "quantity": h.quantity,
            "buy_price": h.buy_price,
            "current_price": current_price,
            **pnl,
            "xirr": holding_xirr,
            "monte_carlo": mc,
            "risk": risk,
        })

    total_pnl = total_current - total_invested
    total_pnl_pct = round((total_pnl / total_invested) * 100, 2) if total_invested else 0

    return numpy_to_python({
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": total_pnl_pct,
        },
        "holdings": holdings_data,
    })


@router.get("/history")
async def portfolio_history(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user["sub"])
        .order_by(PortfolioSnapshot.snapshot_date)
        .limit(365)
    )
    snapshots = result.scalars().all()
    return [
        {
            "date": str(s.snapshot_date),
            "total_value": float(s.total_value),
            "total_invested": float(s.total_cost),
            "pnl": float(s.total_value - s.total_cost),
        }
        for s in snapshots
    ]


@router.post("/test-snapshot")
async def test_snapshot():
    from workers.amfi_cron import take_daily_snapshot
    await take_daily_snapshot()
    return {"message": "Snapshot triggered"}
