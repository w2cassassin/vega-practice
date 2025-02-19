from io import BytesIO
import httpx
import asyncio
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

        group_count = len(standardized_content.keys()) if standardized_content else 0

        print(standardized_content)
        new_file = ScheduleFile(
            original_name=file.filename,
            file_data=file_data,
            standardized_content=standardized_content,
            group_count=group_count,
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

    async def _make_request_with_retry(self, client, url, params=None, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)

    async def download_group_schedules(self, groups):
        combined_content = {}
        combined_ics_data = BytesIO()

        for group in groups:
            try:
                async with httpx.AsyncClient() as client:
                    search_response = await self._make_request_with_retry(
                        client,
                        "https://schedule-of.mirea.ru/schedule/api/search",
                        params={"match": group, "limit": 1},
                    )
                    search_data = search_response.json()

                    if not search_data.get("data"):
                        continue

                    ics_link = search_data["data"][0].get("iCalLink")
                    if not ics_link:
                        continue

                    ics_response = await self._make_request_with_retry(client, ics_link)
                    ics_data = ics_response.content

                    try:
                        schedule_data = self.content_converter.convert(ics_data, "ics")
                        if schedule_data:
                            combined_content.update(schedule_data)
                            combined_ics_data.write(ics_data)
                    except ValueError as e:
                        print(f"Error converting schedule for group {group}: {e}")
                        continue

            except httpx.HTTPError as e:
                print(f"Error downloading schedule for group {group}: {e}")
                continue

        if not combined_content:
            raise ValueError("No schedules could be downloaded")

        new_file = ScheduleFile(
            original_name=f"combined_schedule_{len(groups)}_groups.ics",
            file_data=combined_ics_data.getvalue(),
            standardized_content=combined_content,
            group_count=len(combined_content),
        )

        self.db_session.add(new_file)
        await self.db_session.commit()
        await self.db_session.refresh(new_file)

        return new_file
