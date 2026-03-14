import asyncio
import json
import os
import websockets
from dotenv import load_dotenv

load_dotenv()

SYMBOLS = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA"]
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

async def finnhub_price_worker():
    from core.redis import get_redis
    redis_client = await get_redis()
    uri = f"wss://ws.finnhub.io?token={FINNHUB_KEY}"
    print("🔄 Connecting to Finnhub WebSocket...")

    async for ws in websockets.connect(uri):
        try:
            print("✅ Finnhub WebSocket connected")
            for symbol in SYMBOLS:
                await ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))

            async for msg in ws:
                data = json.loads(msg)
                if data.get("type") != "trade":
                    continue
                for trade in data.get("data", []):
                    symbol = trade["s"].lower().replace(".", "_")
                    price  = str(trade["p"])
                    await redis_client.setex(f"price:stock:{symbol}", 30, price)
                    await redis_client.publish(
                        "prices",
                        json.dumps({"symbol": symbol, "price": price, "type": "stock"})
                    )
        except Exception as e:
            print(f"⚠️ Finnhub WS error: {e}, reconnecting...")
            await asyncio.sleep(3)
