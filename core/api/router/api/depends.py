from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.session import get_session
from core.services.file_manager import FileManager
from core.services.schedule_compare import ScheduleCompareService
from core.services.schedule_service import ScheduleService


async def get_file_manager(
    db_session: AsyncSession = Depends(get_session),
) -> FileManager:
    return FileManager(db_session=db_session)


async def get_compare_service() -> FileManager:
    return ScheduleCompareService()


async def get_schedule_service(
    db_session: AsyncSession = Depends(get_session),
) -> ScheduleService:
    return ScheduleService(db=db_session)
