import json
import httpx
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.redis import get_redis
from models.price_history import PriceHistory
from services.price_backfill import ensure_mf_history

router = APIRouter(prefix="/api/mutual", tags=["MF Compat"])
MFAPI_BASE = "https://api.mfapi.in"


async def _get_nav_series(scheme_code: str, db: AsyncSession, redis) -> list[dict]:
    cache_key = f"pseries:mf:{scheme_code}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.symbol == scheme_code, PriceHistory.asset_type == "mutualfund")
        .order_by(PriceHistory.price_date)
    )
    rows = result.scalars().all()

    if len(rows) < 30:
        await ensure_mf_history(scheme_code, db)
        result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.symbol == scheme_code, PriceHistory.asset_type == "mutualfund")
            .order_by(PriceHistory.price_date)
        )
        rows = result.scalars().all()

    series = [{"date": str(r.price_date), "nav": float(r.close_price)} for r in rows]
    if series:
        await redis.setex(cache_key, 1800, json.dumps(series))
    return series


def _nav_df(series: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(series)
    df["date"] = pd.to_datetime(df["date"])
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df.dropna(subset=["nav"], inplace=True)
    df.sort_values("date", inplace=True)
    df["returns"] = df["nav"].pct_change()
    return df


def _risk_metrics(df: pd.DataFrame) -> dict:
    returns = df["returns"].dropna()
    ann_vol = float(returns.std() * (252 ** 0.5))
    ann_ret = float((returns.mean() + 1) ** 252 - 1)
    sharpe = float((ann_ret - 0.06) / ann_vol) if ann_vol > 0 else 0.0
    return {
        "annualized_volatility": ann_vol,
        "annualized_return": ann_ret,
        "sharpe_ratio": sharpe,
        "returns": [
            {"date": str(r["date"])[:10], "returns": round(float(r["returns"]), 8)}
            for _, r in df.iterrows() if not pd.isna(r["returns"])
        ],
    }


def _monte_carlo(df: pd.DataFrame) -> dict:
    returns = df["returns"].dropna()
    if len(returns) < 10:
        return {"message": "Insufficient data"}
    mu, sigma = float(returns.mean()), float(returns.std())
    last_nav = float(df["nav"].iloc[-1])
    num_simulations, days = 1000, 252
    sims = np.zeros((num_simulations, days))
    sims[:, 0] = last_nav
    for t in range(1, days):
        sims[:, t] = sims[:, t - 1] * (1 + np.random.normal(mu, sigma, num_simulations))
    sim_paths = [
        {"name": f"Simulation {i + 1}",
         "data": [{"day": d, "value": float(sims[i, d])} for d in range(0, days, 5)]}
        for i in range(4)
    ]
    historical_predicted = [
        {"day": d, "value": float(np.mean(sims[:, d]))} for d in range(0, days, 5)
    ]
    return {
        "expected_nav": float(np.mean(sims[:, -1])),
        "probability_positive_return": float(np.mean(sims[:, -1] > last_nav) * 100),
        "lower_bound_5th_percentile": float(np.percentile(sims[:, -1], 5)),
        "upper_bound_95th_percentile": float(np.percentile(sims[:, -1], 95)),
        "last_nav": last_nav,
        "simulation_paths": sim_paths,
        "historical_predicted": historical_predicted,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/schemes")
async def get_schemes(search: str = "", redis=Depends(get_redis)):
    cache_key = f"mf:schemes:{search.lower()[:50]}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{MFAPI_BASE}/mf", timeout=15)
        if r.status_code != 200:
            return {}
    all_schemes = {item["schemeCode"]: item["schemeName"] for item in r.json()}
    result = (
        {k: v for k, v in all_schemes.items() if search.lower() in v.lower()}
        if search else all_schemes
    )
    await redis.setex(cache_key, 3600, json.dumps(result))
    return result


@router.get("/scheme-details/{scheme_code}")
async def get_scheme_details(scheme_code: str, redis=Depends(get_redis)):
    cache_key = f"mf:meta:{scheme_code}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{MFAPI_BASE}/mf/{scheme_code}", timeout=10)
    if r.status_code != 200:
        raise HTTPException(status_code=404, detail="Scheme not found")
    full = r.json()
    meta = full.get("meta") or {
        "scheme_name": full.get("scheme_name", ""),
        "fund_house": full.get("fund_house", ""),
        "scheme_type": full.get("scheme_type", ""),
        "scheme_category": full.get("scheme_category", ""),
    }
    await redis.setex(cache_key, 3600, json.dumps(meta))
    return meta


@router.get("/historical-nav/{scheme_code}")
async def get_historical_nav(
    scheme_code: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    series = await _get_nav_series(scheme_code, db, redis)
    return series or []


@router.get("/performance-heatmap/{scheme_code}")
async def get_heatmap(
    scheme_code: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    cache_key = f"mf:heatmap:{scheme_code}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    series = await _get_nav_series(scheme_code, db, redis)
    if not series:
        return []
    df = _nav_df(series)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    monthly = df.groupby(["year", "month"]).agg(
        first_nav=("nav", "first"), last_nav=("nav", "last")
    ).reset_index()
    monthly["value"] = ((monthly["last_nav"] - monthly["first_nav"]) / monthly["first_nav"]) * 100
    result = monthly[["year", "month", "value", "last_nav"]].rename(
        columns={"last_nav": "nav"}
    ).to_dict(orient="records")
    await redis.setex(cache_key, 1800, json.dumps(result))
    return result


@router.get("/risk-volatility/{scheme_code}")
async def get_risk(
    scheme_code: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    cache_key = f"mf:risk:{scheme_code}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    series = await _get_nav_series(scheme_code, db, redis)
    if not series:
        return {"annualized_volatility": 0.0, "annualized_return": 0.0, "sharpe_ratio": 0.0, "returns": []}
    result = _risk_metrics(_nav_df(series))
    await redis.setex(cache_key, 3600, json.dumps(result))
    return result


@router.get("/monte-carlo-prediction/{scheme_code}")
async def get_monte_carlo(
    scheme_code: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    cache_key = f"mf:mc:{scheme_code}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    series = await _get_nav_series(scheme_code, db, redis)
    if not series:
        return {"message": "No NAV data"}
    result = _monte_carlo(_nav_df(series))
    await redis.setex(cache_key, 21600, json.dumps(result))
    return result


@router.get("/compare-navs")
async def compare_navs(
    scheme_codes: str = Query(..., description="Comma-separated scheme codes"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    codes = [c.strip() for c in scheme_codes.split(",")]
    comparison = {}
    for code in codes:
        series = await _get_nav_series(code, db, redis)
        if series:
            df = pd.DataFrame(series).set_index("date")["nav"]
            comparison[code] = df
    if not comparison:
        return []
    combined = pd.concat(comparison.values(), axis=1, keys=comparison.keys()).reset_index()
    combined.columns = ["date"] + [f"{c}_nav" for c in comparison.keys()]
    return combined.fillna("").astype(str).to_dict(orient="records")
