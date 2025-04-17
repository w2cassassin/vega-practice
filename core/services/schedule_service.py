import datetime
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
import time

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.types import Date as SQLDate
from core.db.models.schedule_models import (
    ScDisc,
    ScGroup,
    ScPrep,
    ScRasp7,
    ScRasp7Groups,
    ScRasp7Preps,
    ScRasp7Rooms,
    ScRasp18,
    ScRasp18Days,
    ScRasp18Groups,
    ScRasp18Preps,
    ScRasp18Rooms,
)
from core.settings.app_config import settings

# Маппинг дней недели
WEEKDAY_MAP = {
    "Понедельник": 0,
    "Вторник": 1,
    "Среда": 2,
    "Четверг": 3,
    "Пятница": 4,
    "Суббота": 5,
    "Воскресенье": 6,
}

WEEKDAY_MAP_REVERSE = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}

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
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_current_semcode(self) -> int:
        today = datetime.date.today()
        year = today.year
        month = today.month

        # Весенний семестр (февраль-июнь): месяцы 2-6
        if 2 <= month <= 6:
            return year * 10 + 2
        # Осенний семестр (сентябрь-январь следующего года): месяцы 9-12 и 1
        elif month >= 9 or month == 1:
            # Если январь, то семестр относится к предыдущему году
            if month == 1:
                return (year - 1) * 10 + 1
            return year * 10 + 1
        else:
            return year * 10 + 1

    async def get_schedule_info(self) -> Dict[str, Any]:
        """
        Получает информацию о доступных семестрах, версиях расписания и другую метаинформацию
        """
        # Получаем уникальные семкоды и версии из расписания
        q_semcodes = select(ScRasp7.semcode).distinct()
        semcodes = (await self.db.scalars(q_semcodes)).all()

        # Получаем версии для каждого семкода
        versions_by_semcode = {}
        for semcode in semcodes:
            q_versions = (
                select(ScRasp7.version).where(ScRasp7.semcode == semcode).distinct()
            )
            versions = (await self.db.scalars(q_versions)).all()
            versions_by_semcode[semcode] = versions

        # Получаем диапазон дат для каждого семестра
        semester_dates = {}
        for semcode in semcodes:
            q_dates = select(
                func.min(ScRasp18Days.day).label("start_date"),
                func.max(ScRasp18Days.day).label("end_date"),
            ).where(ScRasp18Days.semcode == semcode)

            result = await self.db.execute(q_dates)
            dates = result.first()
            if dates:
                semester_dates[semcode] = {
                    "start_date": (
                        dates.start_date.isoformat() if dates.start_date else None
                    ),
                    "end_date": dates.end_date.isoformat() if dates.end_date else None,
                }

        # Собираем актуальные типы занятий
        lesson_types = {}
        for name, type_id in settings.LESSON_TYPES.items():
            lesson_types[str(type_id)] = name

        # Определяем текущий семкод
        current_semcode = await self.get_current_semcode()

        return {
            "current_semcode": current_semcode,
            "semcodes": semcodes,
            "versions_by_semcode": versions_by_semcode,
            "semester_dates": semester_dates,
            "lesson_types": lesson_types,
        }

    async def get_semester_dates(self, semcode: int) -> Dict[str, Any]:
        """
        Получает даты начала и конца семестра, а также список всех дней семестра
        """
        # Если дат для семестра нет, создаем их
        await self._ensure_18week_days(semcode)

        # Получаем все даты для семестра
        q_days = (
            select(ScRasp18Days)
            .where(ScRasp18Days.semcode == semcode)
            .order_by(ScRasp18Days.day)
        )

        days = (await self.db.scalars(q_days)).all()

        if not days:
            return {
                "semcode": semcode,
                "start_date": None,
                "end_date": None,
                "days": [],
            }

        # Формируем список дней с информацией о неделе и дне недели
        days_list = []
        for day in days:
            days_list.append(
                {
                    "date": day.day.isoformat(),
                    "weekday": day.weekday,
                    "weekday_name": WEEKDAY_MAP_REVERSE.get(day.weekday, ""),
                    "week": day.week,
                    "is_odd_week": day.week % 2 == 1,
                }
            )

        return {
            "semcode": semcode,
            "start_date": days[0].day.isoformat() if days else None,
            "end_date": days[-1].day.isoformat() if days else None,
            "days": days_list,
        }

    async def get_free_slots(
        self,
        semcode: int,
        date_from: datetime.date,
        date_to: datetime.date,
        filter_types: List[Literal["group", "prep", "room"]],
        filter_values: List[str],
    ) -> Dict[str, Dict[str, List[int]]]:
        """
        Находит свободные слоты в расписании для указанных групп, преподавателей или аудиторий
        Возвращает словарь вида:
        {
            "date": {
                "entity_name": [список свободных пар]
            }
        }
        """
        # Получаем расписание для каждого фильтра
        schedules = {}
        for i, filter_type in enumerate(filter_types):
            filter_value = filter_values[i]
            schedule = await self.get_schedule(
                semcode=semcode,
                date_from=date_from,
                date_to=date_to,
                filter_type=filter_type,
                filter_value=filter_value,
            )
            schedules[filter_value] = schedule.get(filter_value, {})

        # Получаем все даты в диапазоне
        q_days = (
            select(ScRasp18Days)
            .where(
                ScRasp18Days.semcode == semcode,
                ScRasp18Days.day >= date_from,
                ScRasp18Days.day <= date_to,
            )
            .order_by(ScRasp18Days.day)
        )

        days = (await self.db.scalars(q_days)).all()

        result = {}
        # Для каждой даты и каждой сущности находим свободные пары
        for day in days:
            date_str = day.day.isoformat()
            result[date_str] = {}

            for entity, schedule in schedules.items():
                # Все возможные пары
                all_pairs = list(range(1, 8))
                # Занятые пары
                busy_pairs = []

                if date_str in schedule:
                    busy_pairs = [int(pair) for pair in schedule[date_str].keys()]

                # Свободные пары = все пары минус занятые пары
                free_pairs = [p for p in all_pairs if p not in busy_pairs]
                result[date_str][entity] = free_pairs

        return result

    async def _get_entity_by_field(self, entity_class, field_name, value):
        col = getattr(entity_class, field_name)

        if (
            hasattr(col, "type")
            and isinstance(col.type, SQLDate)
            and isinstance(value, str)
        ):
            value = datetime.datetime.fromisoformat(value).date()

        stmt = select(entity_class).where(col == value)
        return (await self.db.scalars(stmt)).first()

    async def _process_in_chunks(self, entries, chunk_size=500):
        """Обрабатывает список записей порциями"""
        if not entries:
            return

        for i in range(0, len(entries), chunk_size):
            chunk = entries[i : i + chunk_size]
            self.db.add_all(chunk)
            await self.db.flush()

    def _parse_csv_value(self, value_str, separator=","):
        """Парсит строковое значение, разделенное запятыми, в список"""
        if not value_str:
            return []
        return [item.strip() for item in value_str.split(separator) if item.strip()]

    async def add_or_update_7day_schedule_from_dict(
        self,
        semcode: str,
        version: int,
        data: dict,
    ):
        """
        Добавляет или обновляет 7-дневное расписание из словаря
        Формат входных данных:
        {
          '<название_группы>': {
             '<название_дня_недели>': {
                '<номер_пары>': {
                   'odd': {...},
                   'even': {...}
                }
             }
          }
        }
        """
        group_ids = {}
        disc_ids = {}
        prep_ids = {}

        unique_groups = set()
        unique_discs = set()
        unique_preps = set()

        # Собираем уникальные сущности
        for group_title, weekdays_data in data.items():
            unique_groups.add(group_title)
            for weekday_name, pairs_data in weekdays_data.items():
                for pair_slot, odd_even_data in pairs_data.items():
                    for week_type in ["odd", "even"]:
                        lesson_info = odd_even_data.get(week_type)
                        if lesson_info:
                            unique_discs.add(lesson_info.get("subject", ""))

                            # Обрабатываем преподавателей
                            teacher_str = lesson_info.get("teacher", "")
                            if teacher_str:
                                unique_preps.update(self._parse_csv_value(teacher_str))

        # Создаем словари для быстрого доступа
        for group_title in unique_groups:
            group_ids[group_title] = await self._get_or_create_group(group_title)

        for disc_title in unique_discs:
            disc_ids[disc_title] = await self._get_or_create_disc(disc_title)

        for prep_fio in unique_preps:
            prep_ids[prep_fio] = await self._get_or_create_prep(prep_fio)

        # Удаляем существующие записи
        group_id_list = list(group_ids.values())
        delete_stmt = delete(ScRasp7).where(
            and_(
                ScRasp7.semcode == semcode,
                ScRasp7.version == version,
                ScRasp7.id.in_(
                    select(ScRasp7Groups.rasp7_id).where(
                        ScRasp7Groups.group_id.in_(group_id_list)
                    )
                ),
            )
        )
        await self.db.execute(delete_stmt)
        await self.db.commit()

        rasp7_entries = []
        groups_entries = []
        rooms_entries = []
        preps_entries = []
        rasp7_dates_info = {}

        for group_title, weekdays_data in data.items():
            group_id = group_ids[group_title]

            for weekday_name, pairs_data in weekdays_data.items():
                weekday = WEEKDAY_MAP.get(weekday_name, 0)

                for pair_slot, odd_even_data in pairs_data.items():
                    pair = int(pair_slot.replace("Пара ", ""))

                    # Обрабатываем нечетные недели
                    dates_info = self._process_week_schedule(
                        rasp7_entries=rasp7_entries,
                        groups_entries=groups_entries,
                        rooms_entries=rooms_entries,
                        preps_entries=preps_entries,
                        odd_even_data=odd_even_data,
                        week_type="odd",
                        weeks_array=ODD_WEEKS,
                        semcode=semcode,
                        version=version,
                        disc_ids=disc_ids,
                        weekday=weekday,
                        pair=pair,
                        group_id=group_id,
                        prep_ids=prep_ids,
                    )
                    if dates_info and len(rasp7_entries) > 0:
                        rasp7_idx = len(rasp7_entries) - 1
                        rasp7_dates_info[rasp7_idx] = dates_info

                    # Обрабатываем четные недели
                    dates_info = self._process_week_schedule(
                        rasp7_entries=rasp7_entries,
                        groups_entries=groups_entries,
                        rooms_entries=rooms_entries,
                        preps_entries=preps_entries,
                        odd_even_data=odd_even_data,
                        week_type="even",
                        weeks_array=EVEN_WEEKS,
                        semcode=semcode,
                        version=version,
                        disc_ids=disc_ids,
                        weekday=weekday,
                        pair=pair,
                        group_id=group_id,
                        prep_ids=prep_ids,
                    )
                    if dates_info and len(rasp7_entries) > 0:
                        rasp7_idx = len(rasp7_entries) - 1
                        rasp7_dates_info[rasp7_idx] = dates_info

        # Сохраняем данные
        if rasp7_entries:
            await self._process_in_chunks(rasp7_entries)

            # Создаем связи
            related_entries = []

            # Группы
            for rasp7_idx, group_id in groups_entries:
                related_entries.append(
                    ScRasp7Groups(
                        rasp7_id=rasp7_entries[rasp7_idx].id, group_id=group_id
                    )
                )

            # Аудитории
            for rasp7_idx, room in rooms_entries:
                related_entries.append(
                    ScRasp7Rooms(rasp7_id=rasp7_entries[rasp7_idx].id, room=room)
                )

            # Преподаватели
            for rasp7_idx, prep_id in preps_entries:
                related_entries.append(
                    ScRasp7Preps(rasp7_id=rasp7_entries[rasp7_idx].id, prep_id=prep_id)
                )

            await self._process_in_chunks(related_entries)
            await self.db.commit()

            # Создаем отображение ID в БД -> индекс в локальном массиве
            rasp7_db_id_to_idx = {r.id: idx for idx, r in enumerate(rasp7_entries)}

            # Преобразуем даты из индексов в локальном массиве в ID в БД
            db_dates_info = {}
            for idx, dates in rasp7_dates_info.items():
                if idx < len(rasp7_entries):
                    db_id = rasp7_entries[idx].id
                    db_dates_info[db_id] = dates

            # Генерируем 18-недельное расписание
            await self._generate_18week_schedule(
                semcode, version, dates_info=db_dates_info
            )
        else:
            # Если нет записей, просто обновляем 18-недельное расписание
            await self._generate_18week_schedule(semcode, version)

    def _process_week_schedule(
        self,
        rasp7_entries,
        groups_entries,
        rooms_entries,
        preps_entries,
        odd_even_data,
        week_type,
        weeks_array,
        semcode,
        version,
        disc_ids,
        weekday,
        pair,
        group_id,
        prep_ids,
    ):
        """Обрабатывает расписание для конкретного типа недели (четная/нечетная)"""
        lesson_info = odd_even_data.get(week_type)
        if not lesson_info:
            return None

        # Создаем запись расписания
        rasp7 = ScRasp7(
            semcode=semcode,
            version=version,
            disc_id=disc_ids.get(lesson_info.get("subject", ""), 0),
            weekday=weekday,
            pair=pair,
            weeksarray=weeks_array,
            weekstext=",".join(map(str, weeks_array)),
            worktype=settings.LESSON_TYPES.get(lesson_info.get("lesson_type", "ПР"), 0),
        )
        rasp7_entries.append(rasp7)
        rasp7_idx = len(rasp7_entries) - 1

        groups_entries.append((rasp7_idx, group_id))

        room_str = lesson_info.get("room", "")
        rooms = self._parse_csv_value(room_str)
        for room in rooms:
            rooms_entries.append((rasp7_idx, room))

        teacher_str = lesson_info.get("teacher", "")
        teachers = self._parse_csv_value(teacher_str)
        for teacher in teachers:
            preps_entries.append((rasp7_idx, prep_ids.get(teacher, 0)))

        return {
            "date_start": lesson_info.get("date_start"),
            "date_end": lesson_info.get("date_end"),
            "dates": lesson_info.get("dates", []),
        }

    async def _ensure_18week_days(self, semcode: int) -> None:
        """Ensures that all necessary ScRasp18Days entries exist for the semester."""
        q = select(ScRasp18Days).where(ScRasp18Days.semcode == semcode)
        existing_days = (await self.db.scalars(q)).all()
        if existing_days:
            return

        # Получаем год и семестр из семкода
        year = semcode // 10
        semester = semcode % 10

        # Определяем дату начала семестра
        if semester == 1:  # Осенний семестр (сентябрь)
            sept_first = datetime.date(year, 9, 1)
            # Определяем первый понедельник (день недели 0)
            days_ahead = 0 - sept_first.weekday()
            if days_ahead < 0:
                days_ahead += 7
            semester_start = sept_first + datetime.timedelta(days=days_ahead)
        else:  # Весенний семестр (февраль)
            feb_first = datetime.date(year, 2, 1)
            # Определяем первый понедельник (день недели 0)
            days_ahead = 0 - feb_first.weekday()
            if days_ahead < 0:
                days_ahead += 7
            # Сдвигаем начало весеннего семестра на неделю вперёд (пропускаем каникулы)
            semester_start = feb_first + datetime.timedelta(days=days_ahead + 7)

        for week in range(1, 19):
            for weekday in range(7):
                current_date = semester_start + datetime.timedelta(
                    weeks=week - 1, days=weekday
                )
                day_entry = ScRasp18Days(
                    semcode=semcode, day=current_date, weekday=weekday, week=week
                )
                self.db.add(day_entry)

        await self.db.commit()

    async def _generate_18week_schedule(
        self,
        semcode: int,
        version: int,
        start_date: Optional[datetime.date] = None,
        dates_info: Optional[Dict[int, Dict[str, Any]]] = None,
    ):
        """Генерирует 18-недельное расписание на основе 7-дневного"""
        await self._ensure_18week_days(semcode)

        if start_date is None:
            start_date = datetime.date.today()

        if dates_info is None:
            dates_info = {}

        # Для отладки - выводим информацию о датах
        print(f"Dates info keys count: {len(dates_info)}")
        for db_id, date_info in dates_info.items():
            print(
                f"Entry DB ID {db_id}: start={date_info.get('date_start')}, end={date_info.get('date_end')}, dates count={len(date_info.get('dates', []))}"
            )

        # Удаляем существующее расписание начиная с start_date
        q_days_future = select(ScRasp18Days.id).where(
            ScRasp18Days.semcode == semcode, ScRasp18Days.day >= start_date
        )
        future_day_ids = (await self.db.scalars(q_days_future)).all()
        if future_day_ids:
            await self.db.execute(
                delete(ScRasp18).where(ScRasp18.day_id.in_(future_day_ids))
            )
            await self.db.commit()

        # Получаем 7-дневное расписание со связанными данными
        q_rasp7 = (
            select(ScRasp7)
            .where(ScRasp7.semcode == semcode, ScRasp7.version == version)
            .options(
                selectinload(ScRasp7.groups),
                selectinload(ScRasp7.rooms),
                selectinload(ScRasp7.preps),
            )
        )
        rasp7_entries = (await self.db.scalars(q_rasp7)).all()
        if not rasp7_entries:
            return

        rasp7_id_to_dates = dates_info

        rasp7_by_weekday = {}
        for r7 in rasp7_entries:
            if r7.id in rasp7_id_to_dates:
                if r7.weekday not in rasp7_by_weekday:
                    rasp7_by_weekday[r7.weekday] = []
                rasp7_by_weekday[r7.weekday].append(r7)

        q_days = (
            select(ScRasp18Days)
            .where(ScRasp18Days.semcode == semcode, ScRasp18Days.day >= start_date)
            .order_by(ScRasp18Days.day)
        )
        days = (await self.db.scalars(q_days)).all()

        rasp18_entries = []
        related_entries = {"groups": [], "rooms": [], "preps": []}

        for day in days:
            weekday = day.weekday
            week = day.week
            current_date = day.day

            if weekday not in rasp7_by_weekday:
                continue

            for r7 in rasp7_by_weekday[weekday]:
                if week not in r7.weeksarray:
                    continue

                is_valid_date = True

                date_info = rasp7_id_to_dates.get(r7.id)
                if not date_info:
                    continue

                specific_dates = date_info.get("dates", [])
                if specific_dates:
                    is_valid_date = current_date.isoformat() in specific_dates
                else:
                    date_start = date_info.get("date_start")
                    if date_start:
                        date_start_obj = self._parse_date(date_start)
                        if date_start_obj and current_date < date_start_obj:
                            is_valid_date = False

                    date_end = date_info.get("date_end")
                    if date_end:
                        date_end_obj = self._parse_date(date_end)
                        if date_end_obj and current_date > date_end_obj:
                            is_valid_date = False

                if not is_valid_date:
                    continue

                # Создаем запись о паре
                timestart, timeend = get_pair_time(r7.pair)
                rasp18 = ScRasp18(
                    semcode=semcode,
                    day_id=day.id,
                    pair=r7.pair,
                    kind=0,
                    worktype=r7.worktype,
                    disc_id=r7.disc_id,
                    timestart=timestart,
                    timeend=timeend,
                )
                rasp18_entries.append(rasp18)
                entry_idx = len(rasp18_entries) - 1

                # Добавляем группы
                for group in r7.groups:
                    related_entries["groups"].append((entry_idx, group.group_id))

                # Добавляем аудитории
                for room in r7.rooms:
                    related_entries["rooms"].append((entry_idx, room.room))

                # Добавляем преподавателей
                for prep in r7.preps:
                    related_entries["preps"].append((entry_idx, prep.prep_id))

        # Сохраняем основные записи в БД
        if rasp18_entries:
            await self._process_in_chunks(rasp18_entries)

            # Создаем связанные записи
            all_related = []

            # Группы
            for entry_idx, group_id in related_entries["groups"]:
                all_related.append(
                    ScRasp18Groups(
                        rasp18_id=rasp18_entries[entry_idx].id, group_id=group_id
                    )
                )

            # Аудитории
            for entry_idx, room in related_entries["rooms"]:
                all_related.append(
                    ScRasp18Rooms(rasp18_id=rasp18_entries[entry_idx].id, room=room)
                )

            # Преподаватели
            for entry_idx, prep_id in related_entries["preps"]:
                all_related.append(
                    ScRasp18Preps(
                        rasp18_id=rasp18_entries[entry_idx].id, prep_id=prep_id
                    )
                )

            # Сохраняем связанные записи
            await self._process_in_chunks(all_related)
            await self.db.commit()

    async def get_schedule(
        self,
        semcode: int,
        date_from: datetime.date,
        date_to: datetime.date,
        filter_type: str,  # group/prep/room
        filter_value: str,
    ) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
        """
        Возвращает расписание в формате:
        {
          "<группа или преподаватель или аудитория>": {
             "ГГГГ-ММ-ДД": {
                "1": {
                  "subject": "...",
                  "teacher": "...",
                  "room": "...",
                  "lesson_type": "...",
                  "lesson_type_id": ...
                },
                "2": {...},
                ...
             },
             "ГГГГ-ММ-ДД": {...}
           }
        }
        """
        # Получаем нужные дни
        q_days = select(ScRasp18Days).where(
            ScRasp18Days.semcode == semcode,
            ScRasp18Days.day >= date_from,
            ScRasp18Days.day <= date_to,
        )
        day_objs = (await self.db.scalars(q_days)).all()
        if not day_objs:
            return {}

        day_ids = [d.id for d in day_objs]
        # Мапа day_id -> дата
        day_id_to_date = {d.id: d.day for d in day_objs}

        q = (
            select(ScRasp18)
            .where(ScRasp18.day_id.in_(day_ids))
            .options(
                selectinload(ScRasp18.discipline),
                selectinload(ScRasp18.groups).options(
                    selectinload(ScRasp18Groups.group)
                ),
                selectinload(ScRasp18.rooms),
                selectinload(ScRasp18.preps).options(selectinload(ScRasp18Preps.prep)),
            )
        )

        if filter_type == "group":
            # Получаем группу по названию
            group = await self._get_entity_by_field(ScGroup, "title", filter_value)
            if not group:
                return {}

            q = q.where(
                ScRasp18.id.in_(
                    select(ScRasp18Groups.rasp18_id).where(
                        ScRasp18Groups.group_id == group.id
                    )
                )
            )
        elif filter_type == "prep":
            prep = await self._get_entity_by_field(ScPrep, "fio", filter_value)
            if not prep:
                return {}

            q = q.where(
                ScRasp18.id.in_(
                    select(ScRasp18Preps.rasp18_id).where(
                        ScRasp18Preps.prep_id == prep.id
                    )
                )
            )
        elif filter_type == "room":
            q = q.where(
                ScRasp18.id.in_(
                    select(ScRasp18Rooms.rasp18_id).where(
                        ScRasp18Rooms.room == filter_value
                    )
                )
            )
        else:
            return {}

        rasp18_entries = (await self.db.scalars(q)).all()
        if not rasp18_entries:
            return {}

        result = {filter_value: {}}

        for entry in rasp18_entries:
            current_date = day_id_to_date[entry.day_id].isoformat()

            if current_date not in result[filter_value]:
                result[filter_value][current_date] = {}

            disc = entry.discipline.title if entry.discipline else None
            teacher_fios = [p.prep.fio for p in entry.preps if p.prep]
            rooms = [r.room for r in entry.rooms if r.room]
            groups_titles = [g.group.title for g in entry.groups if g.group]

            lesson_type_id = entry.worktype
            lesson_type = next(
                (
                    type_name
                    for type_name, type_id in settings.LESSON_TYPES.items()
                    if type_id == lesson_type_id
                ),
                "-",
            )

            result[filter_value][current_date][str(entry.pair)] = {
                "subject": disc,
                "teacher": ", ".join(teacher_fios) if teacher_fios else None,
                "room": ", ".join(rooms) if rooms else None,
                "lesson_type": lesson_type,
                "lesson_type_id": lesson_type_id,
                "groups": groups_titles,
                "teachers": teacher_fios,
                "rooms": rooms,
                "timestart": entry.timestart,
                "timeend": entry.timeend,
            }

        return result

    async def search_items(
        self, search_type: str, query: str, limit: int = 10
    ) -> list[str]:
        """Поиск групп, преподавателей или аудиторий с помощью ILIKE"""
        if search_type == "group":
            stmt = (
                select(ScGroup.title)
                .where(ScGroup.title.ilike(f"%{query}%"))
                .distinct()
            )
        elif search_type == "prep":
            stmt = select(ScPrep.fio).where(ScPrep.fio.ilike(f"%{query}%")).distinct()
        elif search_type == "subject":
            stmt = (
                select(ScDisc.title).where(ScDisc.title.ilike(f"%{query}%")).distinct()
            )
        elif search_type == "room":
            stmt = (
                select(ScRasp18Rooms.room)
                .where(ScRasp18Rooms.room.ilike(f"%{query}%"))
                .distinct()
            )
        else:
            return []

        result = await self.db.scalars(stmt.limit(limit))
        return [str(item) for item in result.all()]

    async def get_current_week_info(
        self, semcode: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Определяет текущую неделю семестра и ее номер
        Возвращает информацию о текущей неделе:
        - номер недели в семестре (1-18)
        - является ли неделя нечетной
        - дата начала недели
        - дата конца недели
        """
        if not semcode:
            semcode = await self.get_current_semcode()

        await self._ensure_18week_days(semcode)

        today = datetime.date.today()

        q_days = (
            select(ScRasp18Days)
            .where(ScRasp18Days.semcode == semcode)
            .order_by(ScRasp18Days.day)
        )

        all_days = (await self.db.scalars(q_days)).all()
        if not all_days:
            return {
                "week_number": None,
                "is_odd_week": None,
                "week_start": None,
                "week_end": None,
                "current_day": today.isoformat(),
            }

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

                return {
                    "week_number": week_number,
                    "is_odd_week": is_odd_week,
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "current_day": today.isoformat(),
                    "status": "before_semester",
                }
            else:
                last_day = all_days[-1]
                week_number = last_day.week
                is_odd_week = week_number % 2 == 1

                week_days = [d for d in all_days if d.week == week_number]
                week_start = min(d.day for d in week_days)
                week_end = max(d.day for d in week_days)

                return {
                    "week_number": week_number,
                    "is_odd_week": is_odd_week,
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "current_day": today.isoformat(),
                    "status": "after_semester",
                }

        week_number = current_day.week
        is_odd_week = week_number % 2 == 1

        week_days = [d for d in all_days if d.week == week_number]
        week_start = min(d.day for d in week_days)
        week_end = max(d.day for d in week_days)

        return {
            "week_number": week_number,
            "is_odd_week": is_odd_week,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "current_day": today.isoformat(),
            "status": "in_semester",
        }

    async def import_schedule_from_standardized_content(
        self,
        semcode: int,
        version: int,
        standardized_content: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Импортирует расписание из стандартизированного содержимого файла
        в формат 7-дневного расписания и сохраняет в БД

        Args:
            semcode: Код семестра
            version: Версия расписания
            standardized_content: Стандартизированное содержимое файла

        Returns:
            Dict с информацией об импортированных группах
        """
        if not standardized_content:
            raise ValueError("Данные расписания отсутствуют")

        imported_data = {}
        for group, group_schedule in standardized_content.items():
            imported_data[group] = await self._convert_to_week_format(group_schedule)

        # Сохраняем данные в БД
        imported_groups = []
        for group, schedule in imported_data.items():
            if not schedule:
                continue

            await self.add_or_update_7day_schedule_from_dict(
                semcode=semcode, version=version, data={group: schedule}
            )
            imported_groups.append(group)

        return {
            "semcode": semcode,
            "version": version,
            "imported_groups": imported_groups,
            "total_groups": len(imported_groups),
        }

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
    ) -> Dict[str, Any]:
        """Добавляет новую пару в расписание"""
        # Проверяем существование дня и дисциплины
        day = await self._get_entity_by_field(ScRasp18Days, "day", datestr)
        if not day:
            raise ValueError(f"День с датой {datestr} не найден")

        disc_id = await self._get_or_create_disc(disc_title)

        group_ids = [
            await self._get_or_create_group(group_title) for group_title in group_titles
        ]
        prep_ids = [await self._get_or_create_prep(prep_fio) for prep_fio in prep_fios]

        timestart, timeend = get_pair_time(pair)
        rasp18 = ScRasp18(
            semcode=semcode,
            day_id=day.id,
            pair=pair,
            kind=kind,
            worktype=worktype,
            disc_id=disc_id,
            timestart=timestart,
            timeend=timeend,
        )

        self.db.add(rasp18)
        await self.db.flush()

        # Добавляем связанные записи
        await self._add_lesson_relations(rasp18.id, group_ids, "group", ScRasp18Groups)
        await self._add_lesson_relations(rasp18.id, prep_ids, "prep", ScRasp18Preps)
        await self._add_lesson_relations(rasp18.id, rooms, "room", ScRasp18Rooms)

        await self.db.commit()
        return {
            "id": rasp18.id,
            "day": day.day.isoformat(),
            "disc": disc_title,
            "groups": group_titles,
            "teachers": prep_fios,
            "rooms": rooms,
        }

    async def _add_lesson_relations(self, rasp18_id, items, item_type, relation_class):
        """Добавляет связи для занятия (группы, преподаватели, аудитории)"""
        related_records = []

        if item_type == "group":
            for group_id in items:
                group = await self._get_entity_by_field(ScGroup, "id", group_id)
                if group:
                    related_records.append(
                        relation_class(rasp18_id=rasp18_id, group_id=group_id)
                    )
        elif item_type == "prep":
            for prep_id in items:
                prep = await self._get_entity_by_field(ScPrep, "id", prep_id)
                if prep:
                    related_records.append(
                        relation_class(rasp18_id=rasp18_id, prep_id=prep_id)
                    )
        elif item_type == "room":
            for room in items:
                if room.strip():
                    related_records.append(
                        relation_class(rasp18_id=rasp18_id, room=room.strip())
                    )

        # Добавляем записи в БД
        if related_records:
            self.db.add_all(related_records)

    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Парсит дату из строки формата YYYY-MM-DD"""
        try:
            if not date_str:
                return None

            parts = date_str.split("-")
            if len(parts) != 3:
                return None

            return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, TypeError):
            return None

    async def _convert_to_week_format(
        self, group_schedule: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Преобразует расписание группы из формата по датам в формат по дням недели

        Args:
            group_schedule: Расписание группы в формате {дата: {время: данные}}

        Returns:
            Расписание в формате {день_недели: {пара: {odd/even: данные}}}
        """
        week_format = {}

        for date_str, date_schedule in group_schedule.items():
            # Парсим дату
            date_obj = self._parse_date(date_str)
            if not date_obj:
                continue

            weekday = date_obj.weekday()

            # Получаем день недели
            weekday_name = None
            for name, day_num in WEEKDAY_MAP.items():
                if day_num == weekday:
                    weekday_name = name
                    break

            if not weekday_name:
                continue

            if weekday_name not in week_format:
                week_format[weekday_name] = {}

            # Обрабатываем пары на этот день
            for time_slot, lesson in date_schedule.items():
                pair_number = self._get_pair_number_from_time(time_slot)
                if not pair_number:
                    continue

                # Определяем четность недели
                week_number = int(date_obj.strftime("%V"))
                is_odd = week_number % 2 == 1
                week_type = "odd" if is_odd else "even"

                if str(pair_number) not in week_format[weekday_name]:
                    week_format[weekday_name][str(pair_number)] = {}

                week_format[weekday_name][str(pair_number)][week_type] = {
                    "subject": lesson.get("subject", ""),
                    "teacher": lesson.get("teacher", ""),
                    "room": lesson.get("room", ""),
                    "lesson_type": lesson.get("lesson_type", "ПР"),
                }

        return week_format

    def _get_pair_number_from_time(self, time_slot: str) -> Optional[int]:
        """
        Определяет номер пары по времени начала

        Args:
            time_slot: Строка со временем в формате "9:00 - 10:30"

        Returns:
            Номер пары (1-7) или None, если не удалось определить
        """
        start_time = time_slot.split(" - ")[0].strip() if " - " in time_slot else None

        if not start_time:
            return None

        for pair in range(1, 8):
            pair_start, _ = get_pair_time(pair)
            if start_time == pair_start:
                return pair

        return None

    async def _get_or_create_disc(self, title: str) -> int:
        """Получает или создает дисциплину по названию"""
        entity = await self._get_entity_by_field(ScDisc, "title", title)
        if not entity:
            entity = ScDisc(title=title)
            self.db.add(entity)
            await self.db.flush()
        return entity.id

    async def _get_or_create_group(self, title: str) -> int:
        """Получает или создает группу по названию"""
        entity = await self._get_entity_by_field(ScGroup, "title", title)
        if not entity:
            entity = ScGroup(title=title)
            self.db.add(entity)
            await self.db.flush()
        return entity.id

    async def _get_or_create_prep(self, fio: str) -> int:
        """Получает или создает преподавателя по ФИО"""
        entity = await self._get_entity_by_field(ScPrep, "fio", fio)
        if not entity:
            entity = ScPrep(fio=fio)
            self.db.add(entity)
            await self.db.flush()
        return entity.id
