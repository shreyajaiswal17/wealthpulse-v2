import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.redis import init_redis
from core.database import get_db
from api.portfolio import router as portfolio_router
from api.stream import router as stream_router
from api.analytics import router as analytics_router
from workers.amfi_cron import scheduler
from workers.binance_ws import binance_price_worker
from workers.finnhub_ws import finnhub_price_worker
from workers.india_stocks import india_stocks_worker
from services.backfill import backfill_stock_history

app = FastAPI(title="WealthPulse API v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

@app.get("/")
async def root():
    return {"status": "WealthPulse v2 running"}
