import httpx
from fastapi import APIRouter, Query
from core.redis import get_redis

router = APIRouter(prefix="/api/market", tags=["Market"])


# ── MUTUAL FUNDS ───────────────────────────────────────────────────────────

@router.get("/mutualfunds")
async def search_mutualfunds(q: str = Query(..., min_length=1)):
    redis = await get_redis()
    cache_key = f"mf:search:{q.lower()}"
    cached = await redis.get(cache_key)
    if cached:
        import json
        return json.loads(cached)

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.mfapi.in/mf/search?q={q}",
            timeout=10
        )
    results = r.json()[:10]
    import json
    await redis.setex(cache_key, 3600, json.dumps(results))
    return results


@router.get("/mutualfunds/{scheme_code}")
async def get_mutualfund_nav(scheme_code: str):
    redis = await get_redis()
    cache_key = f"mf:nav:{scheme_code}"
    cached = await redis.get(cache_key)
    if cached:
        import json
        return json.loads(cached)

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.mfapi.in/mf/{scheme_code}",
            timeout=10
        )
    data = r.json()
    import json
    await redis.setex(cache_key, 3600, json.dumps(data))
    return data


# ── INDIAN STOCKS ──────────────────────────────────────────────────────────

@router.get("/stocks/india")
async def get_india_stock_price(symbol: str = Query(...)):
    redis = await get_redis()
    key = f"price:stock:{symbol.lower().replace('.', '_')}"
    price = await redis.get(key)
    return {
        "symbol": symbol,
        "price": float(price) if price else None,
        "source": "yfinance",
        "cached": price is not None
    }


# ── US STOCKS ──────────────────────────────────────────────────────────────

@router.get("/stocks/us")
async def get_us_stock_price(symbol: str = Query(...)):
    redis = await get_redis()
    key = f"price:stock:{symbol.lower()}"
    price = await redis.get(key)
    return {
        "symbol": symbol,
        "price": float(price) if price else None,
        "source": "finnhub",
        "cached": price is not None
    }


# ── CRYPTO ─────────────────────────────────────────────────────────────────

@router.get("/crypto")
async def get_crypto_price(symbol: str = Query(...)):
    redis = await get_redis()
    key = f"price:crypto:{symbol.lower()}usdt"
    price = await redis.get(key)
    return {
        "symbol": symbol.upper(),
        "price": float(price) if price else None,
        "source": "binance",
        "cached": price is not None
    }


# ── UNIFIED PRICE LOOKUP ───────────────────────────────────────────────────

@router.get("/price/{asset_type}/{symbol}")
async def get_price(asset_type: str, symbol: str):
    redis = await get_redis()
    key_map = {
        "stock": f"price:stock:{symbol.lower().replace('.', '_')}",
        "crypto": f"price:crypto:{symbol.lower()}usdt",
        "mutualfund": f"nav:{symbol}",
    }
    key = key_map.get(asset_type)
    if not key:
        return {"error": "Invalid asset_type"}
    price = await redis.get(key)
    return {
        "symbol": symbol,
        "asset_type": asset_type,
        "price": float(price) if price else None,
    }
