import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text
from core.database import AsyncSessionLocal

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

async def get_active_scheme_codes() -> set:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT DISTINCT symbol FROM holdings WHERE asset_type='mutualfund'")
        )
        return {row[0] for row in result.fetchall()}

async def parse_and_store_navs():
    active = await get_active_scheme_codes()
    if not active:
        print("No active MF holdings, skipping NAV refresh")
        return

    print(f"Refreshing NAVs for {len(active)} schemes...")
    async with httpx.AsyncClient() as client:
        r = await client.get("https://portal.amfiindia.com/spages/NAVAll.txt", timeout=30)

    # Print a sample of the file to see actual format
    lines = r.text.splitlines()
    print(f"Total lines: {len(lines)}")
    print(f"Sample lines: {lines[:5]}")

    # Check if our scheme exists
    for line in lines:
        if "119551" in line:
            print(f"Found: {line}")
            break
    else:
        print("Scheme 119551 NOT found in AMFI file")

    async with AsyncSessionLocal() as db:
        count = 0
        for line in lines:
            parts = line.split(";")
            if len(parts) < 6:
                continue
            code = parts[0].strip()
            if code not in active:
                continue
            try:
                nav = float(parts[4].strip())
                date_str = parts[5].strip()
                await db.execute(text("""
                    INSERT INTO price_history (symbol, asset_type, price_date, close_price)
                    VALUES (:symbol, 'mutualfund', TO_DATE(:date, 'DD-Mon-YYYY'), :price)
                    ON CONFLICT (symbol, price_date) DO UPDATE SET close_price = :price
                """), {"symbol": code, "date": date_str, "price": nav})
                count += 1
            except Exception as e:
                print(f"Error for {code}: {e}")
                continue
        await db.commit()
        print(f"✅ NAVs updated for {count} schemes")

@scheduler.scheduled_job("cron", hour="10,14,18,21", minute=10)
async def scheduled_nav_refresh():
    await parse_and_store_navs()
