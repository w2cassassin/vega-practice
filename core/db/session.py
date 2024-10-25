from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from core.settings.app_config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
)
Base = declarative_base()
Session = sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession, future=True
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session = Session()
    try:
        yield session
    finally:
        await session.close()
