import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.schedule import (
    ScheduleResult,
    ScheduleInfoModel,
    SemesterDatesModel,
    DayInfoModel,
    LessonInfoModel,
    ScheduleImportResultModel,
    CurrentWeekInfoModel,
    ScheduleResponseModel,
)
from core.settings.app_config import settings
from core.utils.maps import WEEKDAY_MAP, WEEKDAY_MAP_REVERSE
from core.repositories.schedule_repository import ScheduleRepository
from core.services.schedule_processor import ScheduleProcessor
from core.utils.date_utils import get_current_semcode
from core.utils.db_utils import (
    get_or_create_disc,
    get_or_create_group,
    get_or_create_prep,
)

# Маркер для официального расписания
OFFICIAL_MARKER = "*"


# Семестр 18 недель
# нечетные недели: [1,3,5, ... 17]
# четные недели: [2,4,6, ... 18]
ODD_WEEKS = [w for w in range(1, 19) if w % 2 == 1]
EVEN_WEEKS = [w for w in range(1, 19) if w % 2 == 0]


def get_pair_time(pair_number: int) -> Tuple[str, str]:
    """Возвращает время начала и окончания пары по её номеру"""
    pair_times = {
        1: ("9:00", "10:30"),
        2: ("10:40", "12:10"),
        3: ("12:40", "14:10"),
        4: ("14:20", "15:50"),
        5: ("16:20", "17:50"),
        6: ("18:00", "19:30"),
        7: ("19:40", "21:10"),
    }
    return pair_times.get(pair_number, ("00:00", "00:00"))


class ScheduleService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.repo = ScheduleRepository(db_session)
        self.processor = ScheduleProcessor(self.repo, db_session)

    async def get_current_semcode(self) -> int:
        """Получает текущий семкод"""
        return get_current_semcode()

    async def get_schedule_info(self) -> ScheduleInfoModel:
        """
        Получает информацию о доступных семестрах, версиях расписания и другую метаинформацию
        """
        semcodes = await self.repo.get_unique_semcodes()

        versions_by_semcode = {}
        for semcode in semcodes:
            versions = await self.repo.get_versions_for_semcode(semcode)
            versions_by_semcode[str(semcode)] = versions

        semester_dates = {}
        for semcode in semcodes:
            dates = await self.repo.get_semester_date_range(semcode)
            if dates:
                semester_dates[str(semcode)] = dates

        lesson_types = {}
        for name, type_id in settings.LESSON_TYPES.items():
            lesson_types[str(type_id)] = name

        current_semcode = get_current_semcode()

        return ScheduleInfoModel(
            current_semcode=current_semcode,
            semcodes=semcodes,
            versions_by_semcode=versions_by_semcode,
            semester_dates=semester_dates,
            lesson_types=lesson_types,
        )

    async def get_semester_dates(self, semcode: int) -> SemesterDatesModel:
        """
        Получает даты начала и конца семестра, а также список всех дней семестра
        """
        await self.processor.ensure_semester_days(semcode)

        days = await self.repo.get_semester_days(semcode)

        if not days:
            return SemesterDatesModel(
                semcode=semcode,
                start_date=None,
                end_date=None,
                days=[],
            )

        days_list = []
        for day in days:
            days_list.append(
                DayInfoModel(
                    date=day.day.isoformat(),
                    weekday=day.weekday,
                    weekday_name=WEEKDAY_MAP_REVERSE.get(day.weekday, ""),
                    week=day.week,
                    is_odd_week=day.week % 2 == 1,
                )
            )

        return SemesterDatesModel(
            semcode=semcode,
            start_date=days[0].day.isoformat() if days else None,
            end_date=days[-1].day.isoformat() if days else None,
            days=days_list,
        )

    async def get_free_slots(
        self,
        semcode: int,
        date_from: datetime.date,
        date_to: datetime.date,
        filter_types: List[Literal["group", "prep", "room"]],
        filter_values: List[str],
    ) -> Dict[str, Any]:
        """
        Находит свободные слоты в расписании для указанных групп, преподавателей или аудиторий
        """
        free_slots = await self.processor.find_free_slots(
            semcode=semcode,
            date_from=date_from,
            date_to=date_to,
            filter_types=filter_types,
            filter_values=filter_values,
        )

        return free_slots

    async def get_schedule(
        self,
        semcode: int,
        date_from: datetime.date,
        date_to: datetime.date,
        filter_type: str,  # group/prep/room
        filter_value: str,
    ) -> ScheduleResponseModel:
        """
        Возвращает расписание для указанной сущности в диапазоне дат
        """
        days = await self.repo.get_days_in_range(semcode, date_from, date_to)
        if not days:
            return ScheduleResponseModel(root={})

        day_ids = [d.id for d in days]

        entries = await self.repo.get_schedule_for_entity(
            day_ids, filter_type, filter_value
        )

        if not entries:
            return ScheduleResponseModel(root={})

        result = await self.processor.format_schedule_response(
            semcode, days, entries, filter_value
        )

        return ScheduleResponseModel(root=result)

    async def search_items(
        self, search_type: str, query: str, limit: int = 10
    ) -> List[str]:
        """Поиск групп, преподавателей или аудиторий"""
        results = await self.repo.search_entities(search_type, query, limit)
        return results

    async def get_current_week_info(
        self, semcode: Optional[int] = None
    ) -> CurrentWeekInfoModel:
        """
        Определяет текущую неделю семестра и ее номер
        """
        if not semcode:
            semcode = get_current_semcode()

        await self.processor.ensure_semester_days(semcode)

        today = datetime.date.today()

        all_days = await self.repo.get_semester_days(semcode)
        if not all_days:
            return CurrentWeekInfoModel(
                week_number=None,
                is_odd_week=None,
                week_start=None,
                week_end=None,
                current_day=today.isoformat(),
            )

        current_day = None
        for day in all_days:
            if day.day <= today and (current_day is None or day.day > current_day.day):
                current_day = day

        if current_day is None:
            if today < all_days[0].day:
                first_day = all_days[0]
                week_number = first_day.week
                is_odd_week = week_number % 2 == 1

                week_days = [d for d in all_days if d.week == week_number]
                week_start = min(d.day for d in week_days)
                week_end = max(d.day for d in week_days)

                return CurrentWeekInfoModel(
                    week_number=week_number,
                    is_odd_week=is_odd_week,
                    week_start=week_start.isoformat(),
                    week_end=week_end.isoformat(),
                    current_day=today.isoformat(),
                    status="before_semester",
                )
            else:
                last_day = all_days[-1]
                week_number = last_day.week
                is_odd_week = week_number % 2 == 1

                week_days = [d for d in all_days if d.week == week_number]
                week_start = min(d.day for d in week_days)
                week_end = max(d.day for d in week_days)

                return CurrentWeekInfoModel(
                    week_number=week_number,
                    is_odd_week=is_odd_week,
                    week_start=week_start.isoformat(),
                    week_end=week_end.isoformat(),
                    current_day=today.isoformat(),
                    status="after_semester",
                )

        week_number = current_day.week
        is_odd_week = week_number % 2 == 1

        week_days = [d for d in all_days if d.week == week_number]
        week_start = min(d.day for d in week_days)
        week_end = max(d.day for d in week_days)

        return CurrentWeekInfoModel(
            week_number=week_number,
            is_odd_week=is_odd_week,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            current_day=today.isoformat(),
            status="in_semester",
        )

    async def import_schedule_from_standardized_content(
        self,
        semcode: int,
        version: int,
        standardized_content: Dict[str, ScheduleResult],
        is_official: bool = False,
    ) -> ScheduleImportResultModel:
        """
        Импортирует расписание из стандартизированного содержимого файла
        """
        return await self.processor.import_schedule(
            semcode=semcode,
            version=version,
            data=standardized_content,
            is_official=is_official,
        )

    async def add_lesson(
        self,
        semcode: int,
        datestr: str,
        pair: int,
        kind: int,
        worktype: int,
        disc_title: str,
        group_titles: List[str],
        prep_fios: List[str],
        rooms: List[str],
        is_official: bool = False,
        weeks: Optional[List[int]] = None,
    ) -> Union[LessonInfoModel, Dict[str, Any]]:
        """
        Добавляет новую пару в расписание
        """

        day = await self.repo.get_day_by_date(semcode, datestr)
        if not day:
            raise ValueError(f"День с датой {datestr} не найден")

        disc_id = await get_or_create_disc(self.db_session, disc_title, is_official)
        group_ids = [
            await get_or_create_group(self.db_session, group_title, is_official)
            for group_title in group_titles
        ]
        prep_ids = [
            await get_or_create_prep(self.db_session, prep_fio, is_official)
            for prep_fio in prep_fios
        ]

        if is_official:
            rooms = [
                (
                    f"{room}{OFFICIAL_MARKER}"
                    if not room.endswith(OFFICIAL_MARKER)
                    else room
                )
                for room in rooms
            ]

        if not weeks:
            return await self.processor.create_single_lesson(
                semcode=semcode,
                day_id=day.id,
                pair=pair,
                kind=kind,
                worktype=worktype,
                disc_id=disc_id,
                group_ids=group_ids,
                prep_ids=prep_ids,
                rooms=rooms,
                datestr=datestr,
            )

        semester_dates = await self.get_semester_dates(semcode)

        created_lessons = []
        errors = []

        for week_number in weeks:
            target_day = next(
                (
                    d
                    for d in semester_dates.days
                    if d.week == week_number and d.weekday == day.weekday
                ),
                None,
            )

            if not target_day:
                continue

            target_datestr = target_day.date
            target_day_obj = await self.repo.get_day_by_date(semcode, target_datestr)

            if not target_day_obj:
                continue

            try:
                lesson_info = await self.processor.create_single_lesson(
                    semcode=semcode,
                    day_id=target_day_obj.id,
                    pair=pair,
                    kind=kind,
                    worktype=worktype,
                    disc_id=disc_id,
                    group_ids=group_ids,
                    prep_ids=prep_ids,
                    rooms=rooms,
                    datestr=target_datestr,
                )
                created_lessons.append(lesson_info)
            except ValueError as e:
                errors.append(
                    {"week": week_number, "date": target_datestr, "error": str(e)}
                )

        await self.db_session.commit()

        return {
            "created_lessons": created_lessons,
            "errors": errors,
            "total_created": len(created_lessons),
            "total_errors": len(errors),
        }

    async def delete_lesson(self, lesson_id: int) -> Dict[str, Any]:
        """Удаляет пару из расписания"""
        lesson = await self.repo.get_lesson_with_related(lesson_id)
        if not lesson:
            return {"ok": True}
        await self.repo.delete_lesson(lesson_id)
        return {"ok": True}

    async def move_lesson(
        self,
        lesson_id: int,
        target_date: str,
        target_pair: int,
        reason: str = "",
        comment: str = "",
    ) -> Dict[str, Any]:
        """Создает перенос пары на другую дату/время"""
        return await self.processor.move_lesson(
            lesson_id=lesson_id,
            target_date=target_date,
            target_pair=target_pair,
            reason=reason,
            comment=comment,
        )
