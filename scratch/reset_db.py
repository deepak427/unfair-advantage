import asyncio
import asyncpg
from config.settings import settings

async def reset_db():
    print(f"Connecting to {settings.database_url[:20]}...")
    conn = await asyncpg.connect(settings.database_url)
    try:
        print("Dropping legacy tables...")
        await conn.execute("DROP TABLE IF EXISTS chunks CASCADE")
        await conn.execute("DROP TABLE IF EXISTS books CASCADE")
        print("Success: Tables dropped. Ready for 3072-dim recreation.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(reset_db())
