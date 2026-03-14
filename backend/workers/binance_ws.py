import asyncio
import json
import websockets

COINS = ["btcusdt", "ethusdt", "solusdt", "bnbusdt", "adausdt", "dogeusdt"]

async def binance_price_worker():
    from core.redis import redis_client  # import here, after init_redis() has run
    streams = "/".join(f"{c}@ticker" for c in COINS)
    uri = f"wss://stream.binance.com:9443/stream?streams={streams}"
    print("🔄 Connecting to Binance WebSocket...")

    async for ws in websockets.connect(uri):
        try:
            print("✅ Binance WebSocket connected")
            async for msg in ws:
                data = json.loads(msg)["data"]
                symbol = data["s"].lower()
                price  = data["c"]
                await redis_client.setex(f"price:crypto:{symbol}", 30, price)
                await redis_client.publish(
                    "prices",
                    json.dumps({"symbol": symbol, "price": price, "type": "crypto"})
                )
        except Exception as e:
            print(f"⚠️ Binance WS error: {e}, reconnecting...")
            await asyncio.sleep(3)
