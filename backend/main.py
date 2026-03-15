import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from core.limiter import limiter
from core.redis import init_redis
from core.database import get_db
from api.portfolio import router as portfolio_router
from api.stream import router as stream_router
from api.analytics import router as analytics_router
from api.market import router as market_router
from api.ai import router as ai_router
from workers.amfi_cron import scheduler
from workers.binance_ws import binance_price_worker
from workers.finnhub_ws import finnhub_price_worker
from workers.india_stocks import india_stocks_worker
from services.backfill import backfill_stock_history

app = FastAPI(title="WealthPulse API v2")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://wealthpulse.vercel.app",  # replace with your actual Vercel URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_redis()
    asyncio.create_task(binance_price_worker())
    asyncio.create_task(finnhub_price_worker())
    asyncio.create_task(india_stocks_worker())
    scheduler.start()

    async def run_backfill():
        async for db in get_db():
            await backfill_stock_history(db)
            break

    asyncio.create_task(run_backfill())

    print("WealthPulse v2 started")

app.include_router(portfolio_router)
app.include_router(stream_router)
app.include_router(analytics_router)
app.include_router(market_router)
app.include_router(ai_router)

@app.get("/")
async def root():
    return {"status": "WealthPulse v2 running"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )
