from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.session import get_session
from core.repositories.file_repository import FileRepository
from core.services.schedule_compare import ScheduleCompareService
from core.services.schedule_service import ScheduleService
from core.services.schedule_downloader import ScheduleDownloader


async def get_file_manager(
    db_session: AsyncSession = Depends(get_session),
) -> FileRepository:
    return FileRepository(db_session=db_session)


async def get_compare_service() -> ScheduleCompareService:
    return ScheduleCompareService()


async def get_schedule_service(
    db_session: AsyncSession = Depends(get_session),
) -> ScheduleService:
    return ScheduleService(db=db_session)


async def get_schedule_downloader() -> ScheduleDownloader:
    return ScheduleDownloader()
