import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.redis import init_redis
from api.portfolio import router as portfolio_router
from workers.amfi_cron import scheduler, parse_and_store_navs

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
    scheduler.start()
    print("WealthPulse v2 started")

app.include_router(portfolio_router)

@app.get("/")
async def root():
    return {"status": "WealthPulse v2 running"}
