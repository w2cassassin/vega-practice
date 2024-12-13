from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.db.models.schedule_files import ScheduleFile
from core.services.content_converter import StandardContentConverter


class FileManager:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.content_converter = StandardContentConverter()

    async def list_files(self, visible=True):
        query = select(ScheduleFile).where(ScheduleFile.visible == visible)
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

    async def save_file(self, file):
        file_data = await file.read()
        file_format = file.filename.split(".")[-1].lower()

        try:
            standardized_content = self.content_converter.convert(
                file_data, file_format
            )
        except ValueError:
            standardized_content = None

        print(standardized_content)
        new_file = ScheduleFile(
            original_name=file.filename,
            file_data=file_data,
            standardized_content=standardized_content,
        )

        self.db_session.add(new_file)
        await self.db_session.commit()
        await self.db_session.refresh(new_file)

        return new_file

    async def save_file_from_bytes(
        self,
        file: BytesIO,
        filename: str,
    ):
        """Сохраняет файл, созданный вручную через BytesIO"""
        file_data = file.getvalue()
        file_format = filename.split(".")[-1].lower()
        try:
            standardized_content = self.content_converter.convert(
                file_data, file_format
            )
        except ValueError:
            standardized_content = None

        new_file = ScheduleFile(
            original_name=filename,
            file_data=file_data,
            standardized_content=standardized_content,
            visible=False,
        )

        self.db_session.add(new_file)
        await self.db_session.commit()
        await self.db_session.refresh(new_file)

        return new_file
