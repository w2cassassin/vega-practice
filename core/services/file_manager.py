from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.db.models.schedule_files import ScheduleFile


class FileManager:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def list_files(self):
        query = select(ScheduleFile)
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def get_file(self, file_id):
        query = select(ScheduleFile).where(ScheduleFile.id == file_id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def delete_file(self, file_id):
        query = delete(ScheduleFile).where(ScheduleFile.id == file_id)
        await self.db_session.execute(query)
        await self.db_session.commit()

    async def load_xlsx_data(self, file_id):
        file_record = await self.get_file(file_id)

        if file_record:
            file_stream = BytesIO(file_record.file_data)
            workbook = load_workbook(file_stream)
            return workbook
        return None

    async def save_xlsx(self, file_data, original_name):
        new_file = ScheduleFile(original_name=original_name, file_data=file_data)

        self.db_session.add(new_file)
        await self.db_session.commit()
        await self.db_session.refresh(new_file)

        return new_file
    
    async def save_file(self, file):
        file_data = await file.read()

        new_file = ScheduleFile(
            original_name=file.filename,
            file_data=file_data
        )

        self.db_session.add(new_file)
        await self.db_session.commit()
        await self.db_session.refresh(new_file)

        return new_file