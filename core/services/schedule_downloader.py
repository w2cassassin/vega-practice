from io import BytesIO
import httpx
import asyncio

from core.schemas.schedule import ScheduleResult
from core.services.converters import StandardContentConverter


class ScheduleDownloader:
    def __init__(self):
        self.content_converter = StandardContentConverter()

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
        group_schedules = {}
        group_ics_data = {}

        semaphore = asyncio.Semaphore(5)

        async def process_group(group):
            async with semaphore:
                try:
                    async with httpx.AsyncClient() as client:
                        search_response = await self._make_request_with_retry(
                            client,
                            "https://schedule-of.mirea.ru/schedule/api/search",
                            params={"match": group, "limit": 1},
                        )
                        search_data = search_response.json()

                        if not search_data.get("data"):
                            return None

                        ics_link = search_data["data"][0].get("iCalLink")
                        if not ics_link:
                            return None

                        ics_response = await self._make_request_with_retry(
                            client, ics_link
                        )
                        ics_data = ics_response.content

                        try:
                            schedule_data = self.content_converter.convert(
                                ics_data, "ics"
                            )
                            if schedule_data:
                                schedule_data.group_name = group
                                return {
                                    "group": group,
                                    "schedule_result": schedule_data,
                                    "ics_data": ics_data,
                                }
                        except ValueError as e:
                            print(
                                f"Ошибка конвертации расписания для группы {group}: {e}"
                            )
                            return None

                except httpx.HTTPError as e:
                    print(f"Ошибка загрузки расписания для группы {group}: {e}")
                    return None

        tasks = [process_group(group) for group in groups]
        results = await asyncio.gather(*tasks)

        success_count = 0
        combined_ics_data = BytesIO()

        for result in results:
            if result:
                success_count += 1
                group = result["group"]
                group_schedules[group] = result["schedule_result"]
                group_ics_data[group] = result["ics_data"]
                combined_ics_data.write(result["ics_data"])

        if not group_schedules:
            raise ValueError("Не удалось загрузить ни одно расписание")

        print(f"Успешно загружено {success_count} из {len(groups)} групп")

        return {
            "original_name": f"combined_schedule_{len(groups)}_groups.ics",
            "file_data": combined_ics_data.getvalue(),
            "group_schedules": group_schedules,
            "group_ics_data": group_ics_data,
            "group_count": len(group_schedules),
        }
