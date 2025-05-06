from typing import Optional, TypeVar, Type, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.db.models.schedule_models import ScDisc, ScGroup, ScPrep

OFFICIAL_MARKER = "*"

ModelType = TypeVar("ModelType", ScDisc, ScGroup, ScPrep)


async def get_entity_by_field(
    db: AsyncSession, model: Type[ModelType], field_name: str, value: Any
) -> Optional[ModelType]:
    """
    Получает сущность из базы данных по значению поля
    """
    col = getattr(model, field_name)
    stmt = select(model).where(col == value)
    return (await db.scalars(stmt)).first()


async def get_or_create_entity(
    db: AsyncSession,
    model: Type[ModelType],
    field_name: str,
    value: str,
    is_official: bool = False,
    additional_fields: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Получает или создает сущность и возвращает ее ID
    """
    search_value = value

    if is_official and not value.endswith(OFFICIAL_MARKER):
        search_value = f"{value}{OFFICIAL_MARKER}"
    elif not is_official and not value.endswith(OFFICIAL_MARKER):
        search_value = value[:-1]

    entity = await get_entity_by_field(db, model, field_name, search_value)

    if not entity:
        entity_data = {field_name: search_value}

        if additional_fields:
            entity_data.update(additional_fields)

        entity = model(**entity_data)
        db.add(entity)
        await db.flush()

    return entity.id


async def get_or_create_disc(
    db: AsyncSession, title: str, is_official: bool = False
) -> int:
    """Получает или создает дисциплину по названию"""
    return await get_or_create_entity(db, ScDisc, "title", title, is_official)


async def get_or_create_group(
    db: AsyncSession, title: str, is_official: bool = False
) -> int:
    """Получает или создает группу по названию"""
    return await get_or_create_entity(db, ScGroup, "title", title, is_official)


async def get_or_create_prep(
    db: AsyncSession,
    fio: str,
    is_official: bool = False,
    additional_fields: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Получает или создает преподавателя по ФИО
    """
    return await get_or_create_entity(
        db, ScPrep, "fio", fio, is_official, additional_fields
    )
