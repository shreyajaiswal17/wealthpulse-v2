# WealthPulse API Entry Point
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from core.limiter import limiter
from core.redis import init_redis
from core.database import get_db
from core.config import settings
from api.portfolio import router as portfolio_router
from api.stream import router as stream_router
from api.analytics import router as analytics_router
from api.market import router as market_router
from api.ai import router as ai_router
from workers.amfi_cron import scheduler, parse_and_store_navs
from workers.binance_ws import binance_price_worker
from workers.finnhub_ws import finnhub_price_worker
from workers.india_stocks import india_stocks_worker
from services.backfill import backfill_stock_history
from services.crypto_backfill import backfill_crypto_history
from api.stock_compat import router as stock_router
from api.mf_compat import router as mf_router
from api.crypto_compat import router as crypto_router

app = FastAPI(title="WealthPulse API v2")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
# FRONTEND_URL is read from the .env file so you can change it without code edits.
# Add more origins to this list if needed (e.g. preview deployments).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        settings.FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
async def startup():
    await init_redis()
    asyncio.create_task(binance_price_worker())
    asyncio.create_task(finnhub_price_worker())
    asyncio.create_task(india_stocks_worker())
    scheduler.start()

    # Run MF NAV refresh once at startup so Redis has nav:{code} for all MF holdings
    asyncio.create_task(parse_and_store_navs())

    async def run_backfill():
        async for db in get_db():
            await backfill_stock_history(db)
            break

    asyncio.create_task(run_backfill())

    async def run_crypto_backfill():
        async for db in get_db():
            await backfill_crypto_history(db)
            break

    asyncio.create_task(run_crypto_backfill())
    print("WealthPulse v2 started")


app.include_router(portfolio_router)
app.include_router(stream_router)
app.include_router(analytics_router)
app.include_router(market_router)
app.include_router(ai_router)
app.include_router(stock_router)
app.include_router(mf_router)
app.include_router(crypto_router)


@app.get("/")
async def root():
    return {"status": "WealthPulse v2 running"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
