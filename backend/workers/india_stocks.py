import asyncio
import json
import yfinance as yf

SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
    "ICICIBANK.NS", "WIPRO.NS", "SBIN.NS", "BAJFINANCE.NS"
]

async def india_stocks_worker():
    from core.redis import get_redis
    redis_client = await get_redis()
    print("🔄 Starting India stocks polling worker (60s interval)...")

    while True:
        try:
            tickers = yf.download(
                tickers=" ".join(SYMBOLS),
                period="1d",
                interval="1m",
                progress=False,
                auto_adjust=True
            )
            closes = tickers["Close"].iloc[-1]

            for symbol in SYMBOLS:
                if symbol not in closes.index:
                    continue
                price = str(round(float(closes[symbol]), 2))
                redis_key = f"price:stock:{symbol.lower().replace('.', '_')}"
                await redis_client.setex(redis_key, 120, price)
                await redis_client.publish(
                    "prices",
                    json.dumps({"symbol": symbol.lower(), "price": price, "type": "india_stock"})
                )

            print(f"✅ India stocks updated — sample RELIANCE: {closes.get('RELIANCE.NS', 'N/A')}")

        except Exception as e:
            print(f"⚠️ India stocks worker error: {e}")

        await asyncio.sleep(60)
