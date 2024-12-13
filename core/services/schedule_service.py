import datetime
from typing import Any, Dict, Optional

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.db.models.schedule_models import (ScDisc, ScGroup, ScPrep, ScRasp7,
                                            ScRasp7Groups, ScRasp7Preps,
                                            ScRasp7Rooms, ScRasp18,
                                            ScRasp18Days, ScRasp18Groups,
                                            ScRasp18Preps, ScRasp18Rooms)
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

# Семестр 18 недель
# нечетные недели: [1,3,5, ... 17]
# четные недели: [2,4,6, ... 18]
ODD_WEEKS = [w for w in range(1, 19) if w % 2 == 1]
EVEN_WEEKS = [w for w in range(1, 19) if w % 2 == 0]


def get_pair_time(pair_number: int) -> (str, str):
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

    async def _get_or_create_disc(self, title: str) -> int:
        q = select(ScDisc).where(ScDisc.title == title)
        disc = (await self.db.scalars(q)).first()
        if not disc:
            disc = ScDisc(title=title)
            self.db.add(disc)
            await self.db.flush()
        return disc.id

    async def _get_or_create_group(self, title: str) -> int:
        q = select(ScGroup).where(ScGroup.title == title)
        grp = (await self.db.scalars(q)).first()
        if not grp:
            grp = ScGroup(title=title)
            self.db.add(grp)
            await self.db.flush()
        return grp.id

    async def _get_or_create_prep(self, fio: str) -> int:
        q = select(ScPrep).where(ScPrep.fio == fio)
        prep = (await self.db.scalars(q)).first()
        if not prep:
            prep = ScPrep(fio=fio)
            self.db.add(prep)
            await self.db.flush()
        return prep.id

    async def add_or_update_7day_schedule_from_dict(
        self,
        semcode: int,
        version: int,
        data: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]],
    ):
        """
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
        for group_title, weekdays_data in data.items():
            group_id = await self._get_or_create_group(group_title)

            # Удаляем старое расписание только для конкретной группы
            group_rasp7_ids = await self.db.scalars(
                select(ScRasp7.id)
                .join(ScRasp7Groups)
                .where(
                    and_(
                        ScRasp7.semcode == semcode,
                        ScRasp7.version == version,
                        ScRasp7Groups.group_id == group_id,
                    )
                )
            )
            if group_rasp7_ids.all():  # если есть записи для удаления
                await self.db.execute(
                    delete(ScRasp7).where(ScRasp7.id.in_(group_rasp7_ids))
                )
                await self.db.commit()

            for weekday_name, pairs_data in weekdays_data.items():
                weekday = WEEKDAY_MAP.get(weekday_name)
                if not weekday and weekday != 0:
                    continue

                for pair_str, odd_even_data in pairs_data.items():
                    pair = int(pair_str)
                    # odd
                    odd_info = odd_even_data.get("odd")
                    if odd_info:
                        await self._create_7day_entry(
                            semcode=semcode,
                            version=version,
                            weekday=weekday,
                            pair=pair,
                            weeksarray=ODD_WEEKS,
                            info=odd_info,
                            group_id=group_id,
                        )

                    # even
                    even_info = odd_even_data.get("even")
                    if even_info:
                        await self._create_7day_entry(
                            semcode=semcode,
                            version=version,
                            weekday=weekday,
                            pair=pair,
                            weeksarray=EVEN_WEEKS,
                            info=even_info,
                            group_id=group_id,
                        )

        await self.db.commit()
        # Генерируем 18-недельное расписание
        await self._generate_18week_schedule(semcode, version)

    async def _create_7day_entry(
        self,
        semcode: int,
        version: int,
        weekday: int,
        pair: int,
        weeksarray: list[int],
        info: Dict[str, Any],
        group_id: int,
    ):
        disc_id = await self._get_or_create_disc(info["subject"])
        prep_id = await self._get_or_create_prep(info["teacher"])
        room = info["room"]
        lesson_type_id = info.get("lesson_type_id", 0)
        # weekstext можно сформировать по weeksarray, или оставить пустым
        weekstext = ",".join(map(str, weeksarray))

        rasp7 = ScRasp7(
            semcode=semcode,
            version=version,
            disc_id=disc_id,
            weekday=weekday,
            pair=pair,
            weeksarray=weeksarray,
            weekstext=weekstext,
            worktype=lesson_type_id,  # lesson_type_id = worktype
        )
        self.db.add(rasp7)
        await self.db.flush()

        # groups
        g_entry = ScRasp7Groups(rasp7_id=rasp7.id, group_id=group_id)
        self.db.add(g_entry)

        # rooms (добавим campus)
        r_entry = ScRasp7Rooms(rasp7_id=rasp7.id, room=room)
        self.db.add(r_entry)

        # preps
        p_entry = ScRasp7Preps(rasp7_id=rasp7.id, prep_id=prep_id)
        self.db.add(p_entry)

    async def _ensure_18week_days(self, semcode: int) -> None:
        """Ensures that all necessary ScRasp18Days entries exist for the semester."""
        q = select(ScRasp18Days).where(ScRasp18Days.semcode == semcode)
        existing_days = (await self.db.scalars(q)).all()
        if existing_days:
            return

        # Расчет дат на начало семестра
        current_year = datetime.datetime.now().year
        sept_first = datetime.date(current_year, 9, 1)
        days_ahead = 0 - sept_first.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        semester_start = sept_first + datetime.timedelta(days=days_ahead)

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
        self, semcode: int, version: int, start_date: Optional[datetime.date] = None
    ):
        await self._ensure_18week_days(semcode)

        if start_date is None:
            start_date = datetime.date.today()

        # Убрать существующее расписание начиная с сегодняшнего дня (или start_date)
        q_days_future = select(ScRasp18Days.id).where(
            ScRasp18Days.semcode == semcode, ScRasp18Days.day >= start_date
        )
        future_day_ids = (await self.db.scalars(q_days_future)).all()
        if future_day_ids:
            await self.db.execute(
                delete(ScRasp18).where(ScRasp18.day_id.in_(future_day_ids))
            )
            await self.db.commit()

        # Получаем все rasp7
        q_rasp7 = (
            select(ScRasp7)
            .where(and_(ScRasp7.semcode == semcode, ScRasp7.version == version))
            .options(
                selectinload(ScRasp7.discipline),
                selectinload(ScRasp7.groups).options(selectinload(ScRasp7Groups.group)),
                selectinload(ScRasp7.rooms),
                selectinload(ScRasp7.preps).options(selectinload(ScRasp7Preps.prep)),
            )
        )
        rasp7_entries = (await self.db.scalars(q_rasp7)).all()

        # Индексируем по weekday
        rasp7_by_weekday = {}
        for r7 in rasp7_entries:
            rasp7_by_weekday.setdefault(r7.weekday, []).append(r7)

        # Получаем дни семестра начиная с start_date
        q_days = (
            select(ScRasp18Days)
            .where(ScRasp18Days.semcode == semcode, ScRasp18Days.day >= start_date)
            .order_by(ScRasp18Days.day)
        )
        all_days = (await self.db.scalars(q_days)).all()

        for day_obj in all_days:
            day_rasp7 = rasp7_by_weekday.get(day_obj.weekday, [])
            for r7 in day_rasp7:
                # Проверяем, попадает ли текущая week в weeksarray этого r7
                if day_obj.week in r7.weeksarray:
                    timestart, timeend = get_pair_time(r7.pair)
                    rasp18_entry = ScRasp18(
                        semcode=semcode,
                        day_id=day_obj.id,
                        pair=r7.pair,
                        kind=0,
                        worktype=r7.worktype,
                        disc_id=r7.disc_id,
                        timestart=timestart,
                        timeend=timeend,
                    )
                    self.db.add(rasp18_entry)
                    await self.db.flush()

                    for g in r7.groups:
                        self.db.add(
                            ScRasp18Groups(
                                rasp18_id=rasp18_entry.id, group_id=g.group_id
                            )
                        )
                    for rm in r7.rooms:
                        self.db.add(
                            ScRasp18Rooms(rasp18_id=rasp18_entry.id, room=rm.room)
                        )
                    for p in r7.preps:
                        self.db.add(
                            ScRasp18Preps(rasp18_id=rasp18_entry.id, prep_id=p.prep_id)
                        )

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
            qg = select(ScGroup).where(ScGroup.title == filter_value)
            grp = (await self.db.scalars(qg)).first()
            if not grp:
                return {}
            group_id = grp.id
            q = q.where(
                ScRasp18.id.in_(
                    select(ScRasp18Groups.rasp18_id).where(
                        ScRasp18Groups.group_id == group_id
                    )
                )
            )
        elif filter_type == "prep":
            qp = select(ScPrep).where(ScPrep.fio == filter_value)
            prep = (await self.db.scalars(qp)).first()
            if not prep:
                return {}
            prep_id = prep.id
            q = q.where(
                ScRasp18.id.in_(
                    select(ScRasp18Preps.rasp18_id).where(
                        ScRasp18Preps.prep_id == prep_id
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

        rasp18_entries = (await self.db.scalars(q)).all()

        if not rasp18_entries:
            return {}

        result = {filter_value: {}}

        for entry in rasp18_entries:
            current_date = day_id_to_date[entry.day_id].isoformat()
            if current_date not in result[filter_value]:
                result[filter_value][current_date] = {}

            disc = entry.discipline.title if entry.discipline else None
            teacher_fios = [p.prep.fio for p in entry.preps]
            groups_titles = [g.group.title for g in entry.groups]
            rooms = entry.rooms
            room_val = rooms[0].room if rooms else None

            teacher = teacher_fios[0] if teacher_fios else None
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
                "teacher": teacher,
                "room": room_val,
                "lesson_type": lesson_type,
                "lesson_type_id": lesson_type_id,
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
