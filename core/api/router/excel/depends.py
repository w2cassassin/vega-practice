from fastapi import Depends

from core.services.excel import ExcelService as Service
from core.services.file_manager import FileManager
from core.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

async def get_service() -> Service:
    return Service()


async def get_file_manager(db_session:AsyncSession = Depends(get_session)) -> FileManager:
    return FileManager(db_session=db_session)