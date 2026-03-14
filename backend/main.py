import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.redis import init_redis

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
    print("WealthPulse v2 started")

@app.get("/")
async def root():
    return {"status": "WealthPulse v2 running"}
