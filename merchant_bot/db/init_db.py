#python -m merchant_bot.db.init_db
import asyncio

from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

from .engine import engine
from .models import Base


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    print("DB is ready: pgvector on, tables created.")


if __name__ == "__main__":
    asyncio.run(init_db())