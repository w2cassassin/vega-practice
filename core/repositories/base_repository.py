from io import BytesIO
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any


class BaseRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_all(self, model_class):
        query = select(model_class)
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, model_class, id):
        query = select(model_class).where(model_class.id == id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, model_class, **kwargs):
        new_obj = model_class(**kwargs)
        self.db_session.add(new_obj)
        await self.db_session.commit()
        return new_obj

    async def create_entities(
        self, entries: List[Any], chunk_size: int = 500
    ) -> List[Any]:
        """
        Универсальный метод для сохранения множества записей в БД
        """
        if not entries:
            return []

        for i in range(0, len(entries), chunk_size):
            chunk = entries[i : i + chunk_size]
            self.db_session.add_all(chunk)
            await self.db_session.flush()

        return entries
