from typing import Dict, List, Optional, Tuple, Any, Set, Union
from sqlalchemy import and_, delete, insert, or_, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import date, datetime

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
    ScRasp18Move,
    ScRasp18Info,
)
from core.utils.db_utils import get_entity_by_field
from core.utils.date_utils import parse_date, get_pair_time
from core.repositories.base_repository import BaseRepository


class ScheduleRepository(BaseRepository):
    """Репозиторий для работы с данными расписания"""

    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session)

    async def get_unique_semcodes(self) -> List[int]:
        """Получает список уникальных семкодов"""
        q_semcodes = select(ScRasp7.semcode).distinct()
        return (await self.db_session.scalars(q_semcodes)).all()

    async def get_versions_for_semcode(self, semcode: int) -> List[int]:
        """Получает список версий для указанного семкода"""
        q_versions = (
            select(ScRasp7.version).where(ScRasp7.semcode == semcode).distinct()
        )
        return (await self.db_session.scalars(q_versions)).all()

    async def get_semester_date_range(self, semcode: int) -> Optional[Dict[str, str]]:
        """Получает диапазон дат для семестра"""
        q_dates = select(
            func.min(ScRasp18Days.day).label("start_date"),
            func.max(ScRasp18Days.day).label("end_date"),
        ).where(ScRasp18Days.semcode == semcode)

        result = await self.db_session.execute(q_dates)
        dates = result.first()

        if dates and dates.start_date and dates.end_date:
            return {
                "start_date": dates.start_date.isoformat(),
                "end_date": dates.end_date.isoformat(),
            }
        return None

    async def get_semester_days(self, semcode: int) -> List[ScRasp18Days]:
        """Получает все дни семестра"""
        q_days = (
            select(ScRasp18Days)
            .where(ScRasp18Days.semcode == semcode)
            .order_by(ScRasp18Days.day)
        )
        return (await self.db_session.scalars(q_days)).all()

    async def get_days_in_range(
        self, semcode: int, date_from: date, date_to: date
    ) -> List[ScRasp18Days]:
        """Получает дни в указанном диапазоне дат"""
        q_days = (
            select(ScRasp18Days)
            .where(
                ScRasp18Days.semcode == semcode,
                ScRasp18Days.day >= date_from,
                ScRasp18Days.day <= date_to,
            )
            .order_by(ScRasp18Days.day)
        )
        return (await self.db_session.scalars(q_days)).all()

    async def get_day_by_date(
        self, semcode: int, date_value: Union[str, date]
    ) -> Optional[ScRasp18Days]:
        """Получает день по дате"""
        if isinstance(date_value, str):
            date_value = parse_date(date_value)
            if not date_value:
                return None

        q_day = select(ScRasp18Days).where(
            ScRasp18Days.semcode == semcode, ScRasp18Days.day == date_value
        )
        return (await self.db_session.scalars(q_day)).first()

    async def check_if_semester_days_exist(self, semcode: int) -> bool:
        """Проверяет, существуют ли дни для семестра"""
        q = select(func.count(ScRasp18Days.id)).where(ScRasp18Days.semcode == semcode)
        count = await self.db_session.scalar(q)
        return count > 0

    async def create_semester_days(self, days_data: List[Dict[str, Any]]) -> None:
        """Создает дни семестра в БД"""
        day_entries = [ScRasp18Days(**day) for day in days_data]
        self.db_session.add_all(day_entries)
        await self.db_session.commit()

    async def get_schedule_for_entity(
        self,
        day_ids: List[int],
        filter_type: str,
        filter_value: Union[str, int],
    ) -> List[ScRasp18]:
        """
        Получает расписание для конкретной сущности (группы, преподавателя, аудитории)
        """
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
            if isinstance(filter_value, int):
                group_id = filter_value
            else:
                group = await get_entity_by_field(
                    self.db_session, ScGroup, "title", filter_value
                )
                if not group:
                    return []
                group_id = group.id

            q = q.where(
                ScRasp18.id.in_(
                    select(ScRasp18Groups.rasp18_id).where(
                        ScRasp18Groups.group_id == group_id
                    )
                )
            )
        elif filter_type == "prep":
            if isinstance(filter_value, int):
                prep_id = filter_value
            else:
                prep = await get_entity_by_field(
                    self.db_session, ScPrep, "fio", filter_value
                )
                if not prep:
                    return []
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
        else:
            return []

        return (await self.db_session.scalars(q)).all()

    async def search_entities(
        self, search_type: str, query: str, limit: int = 10
    ) -> List[str]:
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

        result = await self.db_session.scalars(stmt.limit(limit))
        return [str(item) for item in result.all()]

    async def create_lesson(self, lesson_data: Dict[str, Any]) -> ScRasp18:
        """Создает запись о занятии"""
        rasp18 = ScRasp18(**lesson_data)
        self.db_session.add(rasp18)
        await self.db_session.flush()
        return rasp18

    async def create_lesson_relations(
        self,
        rasp18_id: int,
        group_ids: List[int] = None,
        prep_ids: List[int] = None,
        rooms: List[str] = None,
    ) -> None:
        """Создает связи для занятия (группы, преподаватели, аудитории)"""
        relations = []

        if group_ids:
            for group_id in group_ids:
                relations.append(ScRasp18Groups(rasp18_id=rasp18_id, group_id=group_id))

        if prep_ids:
            for prep_id in prep_ids:
                relations.append(ScRasp18Preps(rasp18_id=rasp18_id, prep_id=prep_id))

        if rooms:
            for room in rooms:
                if room.strip():
                    relations.append(
                        ScRasp18Rooms(rasp18_id=rasp18_id, room=room.strip())
                    )

        if relations:
            self.db_session.add_all(relations)
            await self.db_session.flush()

    async def delete_lesson(self, lesson_id: int) -> None:
        """Удаляет занятие"""
        lesson = await self.db_session.get(ScRasp18, lesson_id)
        if lesson:
            await self.db_session.delete(lesson)
            await self.db_session.commit()

    async def get_lesson_with_related(self, lesson_id: int) -> Optional[ScRasp18]:
        """Получает занятие со связанными данными"""
        q = (
            select(ScRasp18)
            .where(ScRasp18.id == lesson_id)
            .options(
                selectinload(ScRasp18.discipline),
                selectinload(ScRasp18.day),
                selectinload(ScRasp18.groups).options(
                    selectinload(ScRasp18Groups.group)
                ),
                selectinload(ScRasp18.rooms),
                selectinload(ScRasp18.preps).options(selectinload(ScRasp18Preps.prep)),
            )
        )
        return (await self.db_session.scalars(q)).first()

    async def create_lesson_move(self, move_data: Dict[str, Any]) -> ScRasp18Move:
        """Создает запись о переносе занятия"""
        move = ScRasp18Move(**move_data)
        self.db_session.add(move)
        await self.db_session.flush()
        return move

    async def copy_lesson_relations(
        self, src_lesson_id: int, dest_lesson_id: int
    ) -> None:
        """Копирует связанные записи от одной пары к другой"""
        src_groups = await self.db_session.scalars(
            select(ScRasp18Groups).where(ScRasp18Groups.rasp18_id == src_lesson_id)
        )
        for group in src_groups:
            new_group = ScRasp18Groups(
                rasp18_id=dest_lesson_id,
                group_id=group.group_id,
                subgroup=group.subgroup,
            )
            self.db_session.add(new_group)

        src_preps = await self.db_session.scalars(
            select(ScRasp18Preps).where(ScRasp18Preps.rasp18_id == src_lesson_id)
        )
        for prep in src_preps:
            new_prep = ScRasp18Preps(
                rasp18_id=dest_lesson_id,
                prep_id=prep.prep_id,
            )
            self.db_session.add(new_prep)

        src_rooms = await self.db_session.scalars(
            select(ScRasp18Rooms).where(ScRasp18Rooms.rasp18_id == src_lesson_id)
        )
        for room in src_rooms:
            new_room = ScRasp18Rooms(
                rasp18_id=dest_lesson_id,
                room=room.room,
            )
            self.db_session.add(new_room)

        await self.db_session.flush()

    async def check_lesson_conflicts(
        self,
        semcode: int,
        day_id: int,
        pair: int,
        group_ids: List[int] = None,
        prep_ids: List[int] = None,
        rooms: List[str] = None,
    ) -> Dict[str, List[Any]]:
        """
        Проверяет накладки пар и возвращает список конфликтов
        """
        conflicts = {"groups": [], "preps": [], "rooms": []}

        if group_ids:
            for group_id in group_ids:
                group_conflicts = await self.db_session.scalars(
                    select(ScRasp18)
                    .join(ScRasp18Groups, ScRasp18.id == ScRasp18Groups.rasp18_id)
                    .where(
                        ScRasp18.semcode == semcode,
                        ScRasp18.day_id == day_id,
                        ScRasp18.pair == pair,
                        ScRasp18Groups.group_id == group_id,
                    )
                )
                group_conflicts_list = group_conflicts.all()
                if group_conflicts_list:
                    conflicts["groups"].append(
                        {"group_id": group_id, "conflicts": group_conflicts_list}
                    )

        if prep_ids:
            for prep_id in prep_ids:
                prep_conflicts = await self.db_session.scalars(
                    select(ScRasp18)
                    .join(ScRasp18Preps, ScRasp18.id == ScRasp18Preps.rasp18_id)
                    .where(
                        ScRasp18.semcode == semcode,
                        ScRasp18.day_id == day_id,
                        ScRasp18.pair == pair,
                        ScRasp18Preps.prep_id == prep_id,
                    )
                )
                prep_conflicts_list = prep_conflicts.all()
                if prep_conflicts_list:
                    conflicts["preps"].append(
                        {"prep_id": prep_id, "conflicts": prep_conflicts_list}
                    )

        if rooms:
            for room in rooms:
                room_conflicts = await self.db_session.scalars(
                    select(ScRasp18)
                    .join(ScRasp18Rooms, ScRasp18.id == ScRasp18Rooms.rasp18_id)
                    .where(
                        ScRasp18.semcode == semcode,
                        ScRasp18.day_id == day_id,
                        ScRasp18.pair == pair,
                        ScRasp18Rooms.room == room,
                    )
                )
                room_conflicts_list = room_conflicts.all()
                if room_conflicts_list:
                    conflicts["rooms"].append(
                        {"room": room, "conflicts": room_conflicts_list}
                    )

        return conflicts

    async def delete_schedule(
        self,
        model_class,
        semcode: int,
        version: int = None,
        group_ids: List[int] = None,
    ) -> None:
        """
        Универсальный метод для удаления расписания

        """
        if not group_ids:
            delete_stmt = delete(model_class).where(model_class.semcode == semcode)
            if version is not None:
                delete_stmt = delete_stmt.where(model_class.version == version)
            await self.db_session.execute(delete_stmt)
            await self.db_session.commit()
            return

        if model_class == ScRasp7:
            groups_model = ScRasp7Groups
            rasp_id_field = ScRasp7Groups.rasp7_id
        else:
            groups_model = ScRasp18Groups
            rasp_id_field = ScRasp18Groups.rasp18_id

        query = select(rasp_id_field).where(groups_model.group_id.in_(group_ids))

        if model_class == ScRasp18:
            query = query.join(model_class, model_class.id == rasp_id_field)
            query = query.where(model_class.semcode == semcode)

        record_ids = (await self.db_session.scalars(query)).all()

        if record_ids:
            await self.db_session.execute(
                delete(model_class).where(model_class.id.in_(record_ids))
            )
            await self.db_session.commit()

    async def delete_7day_schedule(
        self, semcode: int, version: int, group_ids: List[int] = None
    ) -> None:
        """Удаляет 7-дневное расписание для указанных групп"""
        await self.delete_schedule(ScRasp7, semcode, version, group_ids)

    async def delete_18week_schedule(
        self, semcode: int, group_ids: List[int] = None
    ) -> None:
        """Удаляет 18-недельное расписание для указанных групп"""
        await self.delete_schedule(ScRasp18, semcode, None, group_ids)

    async def create_7day_schedule_entries(
        self, entries: List[ScRasp7], chunk_size: int = 500
    ) -> List[ScRasp7]:
        """Сохраняет записи 7-дневного расписания в БД"""
        return await self.create_entities(entries, chunk_size)

    async def create_18week_schedule_entries(
        self, entries: List[ScRasp18], chunk_size: int = 500
    ) -> List[ScRasp18]:
        """Сохраняет записи 18-недельного расписания в БД"""
        return await self.create_entities(entries, chunk_size)

    async def create_relations(
        self,
        relations: List[Any],
        chunk_size: int = 500,
    ) -> None:
        return await self.create_entities(relations, chunk_size)

    async def create_7day_relations(
        self,
        relations: List[Union[ScRasp7Groups, ScRasp7Rooms, ScRasp7Preps]],
        chunk_size: int = 500,
    ) -> None:
        """Сохраняет связи 7-дневного расписания в БД"""
        await self.create_relations(relations, chunk_size)

    async def create_18week_relations(
        self,
        relations: List[Union[ScRasp18Groups, ScRasp18Rooms, ScRasp18Preps]],
        chunk_size: int = 500,
    ) -> None:
        """Сохраняет связи 18-недельного расписания в БД"""
        await self.create_relations(relations, chunk_size)

    async def get_7day_schedule(self, semcode: int, version: int) -> List[ScRasp7]:
        """Получает 7-дневное расписание со связанными данными"""
        q_rasp7 = (
            select(ScRasp7)
            .where(ScRasp7.semcode == semcode, ScRasp7.version == version)
            .options(
                selectinload(ScRasp7.groups),
                selectinload(ScRasp7.rooms),
                selectinload(ScRasp7.preps),
            )
        )
        return (await self.db_session.scalars(q_rasp7)).all()
