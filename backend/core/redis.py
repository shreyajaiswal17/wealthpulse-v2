import redis.asyncio as aioredis
from core.config import settings

redis_client: aioredis.Redis = None

async def init_redis():
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True
    )
    try:
        await redis_client.ping()
        print("✅ Redis connected")
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")
        # don't crash — workers will fail gracefully later

async def get_redis():
    return redis_client
