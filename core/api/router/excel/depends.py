from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.session import get_session
from core.services.excel import ExcelCompareService
from core.services.excel import ExcelService as Service
from core.services.file_manager import FileManager


async def get_service() -> Service:
    return Service()


async def get_compare_service() -> ExcelCompareService:
    return ExcelCompareService()


async def get_file_manager(
    db_session: AsyncSession = Depends(get_session),
) -> FileManager:
    return FileManager(db_session=db_session)
