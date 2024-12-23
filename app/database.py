import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Create the database directory if it doesn't exist
database_dir = os.path.join(os.path.dirname(__file__), "..", "database")
os.makedirs(database_dir, exist_ok=True)

# Update the DATABASE_URL to use the new directory
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(database_dir, 'seadexrss.db')}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
