from typing import Dict, List, Optional, Union, Any, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime
import logging

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
from core.schemas.schedule import (
    ScheduleResult,
    LessonData,
    WeekSchedule,
    LessonInfoModel,
    ScheduleImportResultModel,
)
from core.repositories.schedule_repository import ScheduleRepository
from core.utils.db_utils import (
    get_or_create_group,
    get_or_create_disc,
    get_or_create_prep,
    get_entity_by_field,
    OFFICIAL_MARKER,
)
from core.utils.parsing_utils import parse_csv_value, parse_pair_number
from core.utils.date_utils import (
    get_pair_time,
    parse_date,
    generate_semester_days,
)
from core.utils.maps import WEEKDAY_MAP


class ScheduleProcessor:
    """
    Класс для обработки данных расписания и их преобразования
    """

    def __init__(self, repo: ScheduleRepository, db_session: AsyncSession):
        self.repo = repo
        self.db_session = db_session

    async def ensure_semester_days(self, semcode: int) -> None:
        """
        Проверяет и при необходимости создает дни семестра
        """
        days_exist = await self.repo.check_if_semester_days_exist(semcode)
        if days_exist:
            return

        days_data = generate_semester_days(semcode)
        await self.repo.create_semester_days(days_data)

    async def validate_lesson_conflicts(
        self,
        semcode: int,
        day_id: int,
        pair: int,
        group_ids: List[int] = None,
        prep_ids: List[int] = None,
        rooms: List[str] = None,
    ) -> None:
        """
        Проверяет конфликты занятий и выбрасывает исключение при их наличии
        """
        conflicts = await self.repo.check_lesson_conflicts(
            semcode, day_id, pair, group_ids, prep_ids, rooms
        )

        if conflicts["groups"]:
            group_id = conflicts["groups"][0]["group_id"]
            group = await get_entity_by_field(self.db_session, ScGroup, "id", group_id)
            raise ValueError(
                f"Группа {group.title if group else group_id} уже имеет пару в это время"
            )

        if conflicts["preps"]:
            prep_id = conflicts["preps"][0]["prep_id"]
            prep = await get_entity_by_field(self.db_session, ScPrep, "id", prep_id)
            raise ValueError(
                f"Преподаватель {prep.fio if prep else prep_id} уже имеет пару в это время"
            )

        if conflicts["rooms"]:
            room = conflicts["rooms"][0]["room"]
            raise ValueError(f"Аудитория {room} уже занята в это время")

        if len(prep_ids) > 0 and len(rooms) > 2:
            raise ValueError(
                "Преподаватель не может находиться одновременно в нескольких аудиториях"
            )

    async def process_7day_schedule_data(
        self,
        data: Dict[str, ScheduleResult],
        is_official: bool = False,
    ):
        """
        Обрабатывает данные 7-дневного расписания и подготавливает их для сохранения
        """
        if not isinstance(data, dict):
            raise ValueError("Данные должны быть словарем с объектами ScheduleResult")

        for group, schedule in data.items():
            if not isinstance(schedule, ScheduleResult):
                raise ValueError(
                    f"Данные для группы {group} должны быть объектом ScheduleResult"
                )

        schedule_data = data
        group_ids = {}
        disc_ids = {}
        prep_ids = {}

        unique_groups = set()
        unique_discs = set()
        unique_preps = set()

        for group_title, schedule_result in schedule_data.items():
            unique_groups.add(group_title)

            for week_number, week_schedule in schedule_result.week_schedules.items():
                for weekday_str, pairs_data in week_schedule.weekday_schedules.items():
                    for pair_slot, lesson_data in pairs_data.items():
                        if lesson_data.subject:
                            unique_discs.add(lesson_data.subject)

                        if lesson_data.teacher:
                            unique_preps.update(parse_csv_value(lesson_data.teacher))

        for group_title in unique_groups:
            group_ids[group_title] = await get_or_create_group(
                self.db_session, group_title, is_official
            )

        for disc_title in unique_discs:
            disc_ids[disc_title] = await get_or_create_disc(
                self.db_session, disc_title, is_official
            )

        for prep_fio in unique_preps:
            prep_ids[prep_fio] = await get_or_create_prep(
                self.db_session, prep_fio, is_official
            )

        return {"group_ids": group_ids, "disc_ids": disc_ids, "prep_ids": prep_ids}

    async def create_7day_schedule(
        self,
        semcode: int,
        version: int,
        data: Dict[str, ScheduleResult],
        entity_ids: Dict[str, Dict[str, int]],
    ) -> Tuple[List[ScRasp7], Dict[str, Dict[str, List[str]]]]:
        """
        Создает записи 7-дневного расписания на основе данных и подготовленных ID сущностей
        """
        group_ids = entity_ids["group_ids"]
        disc_ids = entity_ids["disc_ids"]
        prep_ids = entity_ids["prep_ids"]

        aggregated_lessons = {}

        for group_title, schedule_result in data.items():
            group_id = group_ids[group_title]

            for week_number, week_schedule in schedule_result.week_schedules.items():
                for weekday_str, pairs_data in week_schedule.weekday_schedules.items():

                    weekday = WEEKDAY_MAP.get(weekday_str, 0)

                    for pair_slot, lesson_data in pairs_data.items():
                        pair = parse_pair_number(pair_slot)
                        if pair is None:
                            continue

                        if not lesson_data.subject:
                            continue
                        disc_id = disc_ids.get(lesson_data.subject, 0)
                        worktype = lesson_data.lesson_type_id or 0

                        agg_key = (group_id, weekday, pair, disc_id, worktype)

                        if agg_key not in aggregated_lessons:
                            aggregated_lessons[agg_key] = {
                                "semcode": semcode,
                                "version": version,
                                "disc_id": disc_id,
                                "weekday": weekday,
                                "pair": pair,
                                "worktype": worktype,
                                "weeksarray": [week_number],
                                "groups": set([group_id]),
                                "rooms": set(),
                                "preps": set(),
                            }
                        else:
                            aggregated_lessons[agg_key]["weeksarray"].append(
                                week_number
                            )
                            aggregated_lessons[agg_key]["groups"].add(group_id)

                        if lesson_data.room:
                            rooms = parse_csv_value(lesson_data.room)
                            for room in rooms:
                                aggregated_lessons[agg_key]["rooms"].add(room)

                        if lesson_data.teacher:
                            teachers = parse_csv_value(lesson_data.teacher)
                            for teacher in teachers:
                                prep_id = prep_ids.get(teacher, 0)
                                if prep_id:
                                    aggregated_lessons[agg_key]["preps"].add(prep_id)

        rasp7_entries = []
        groups_entries = []
        rooms_entries = []
        preps_entries = []

        for agg_data in aggregated_lessons.values():
            weeks_array = sorted(list(set(agg_data["weeksarray"])))

            rasp7 = ScRasp7(
                semcode=agg_data["semcode"],
                version=agg_data["version"],
                disc_id=agg_data["disc_id"],
                weekday=agg_data["weekday"],
                pair=agg_data["pair"],
                weeksarray=weeks_array,
                weekstext=",".join(map(str, weeks_array)),
                worktype=agg_data["worktype"],
            )
            rasp7_entries.append(rasp7)
            rasp7_idx = len(rasp7_entries) - 1

            for group_id in agg_data["groups"]:
                groups_entries.append((rasp7_idx, group_id))

            for room in agg_data["rooms"]:
                rooms_entries.append((rasp7_idx, room))

            for prep_id in agg_data["preps"]:
                preps_entries.append((rasp7_idx, prep_id))

        return rasp7_entries, {
            "groups": groups_entries,
            "rooms": rooms_entries,
            "preps": preps_entries,
        }

    async def prepare_7day_relations(
        self,
        rasp7_entries: List[ScRasp7],
        relations_data: Dict[str, Any],
        is_official: bool = False,
    ) -> List[Union[ScRasp7Groups, ScRasp7Rooms, ScRasp7Preps]]:
        """
        Подготавливает связи для 7-дневного расписания
        """
        groups_entries = relations_data["groups"]
        rooms_entries = relations_data["rooms"]
        preps_entries = relations_data["preps"]

        related_entries = []

        for rasp7_idx, group_id in groups_entries:
            related_entries.append(
                ScRasp7Groups(rasp7_id=rasp7_entries[rasp7_idx].id, group_id=group_id)
            )

        for rasp7_idx, room in rooms_entries:
            room_value = room
            if is_official and not room.endswith(OFFICIAL_MARKER):
                room_value = f"{room}{OFFICIAL_MARKER}"
            related_entries.append(
                ScRasp7Rooms(rasp7_id=rasp7_entries[rasp7_idx].id, room=room_value)
            )

        for rasp7_idx, prep_id in preps_entries:
            related_entries.append(
                ScRasp7Preps(rasp7_id=rasp7_entries[rasp7_idx].id, prep_id=prep_id)
            )

        return related_entries

    async def generate_18week_schedule(
        self,
        semcode: int,
        data: Dict[str, ScheduleResult],
        entity_ids: Dict[str, Dict[str, int]] = None,
        is_official: bool = False,
    ) -> None:
        """
        Генерирует 18-недельное расписание на основе входных данных
        """
        await self.ensure_semester_days(semcode)

        group_ids = list(entity_ids["group_ids"].values())
        await self.repo.delete_18week_schedule(semcode, group_ids)

        days = await self.repo.get_semester_days(semcode)
        if not days:
            return

        disc_ids = entity_ids.get("disc_ids", {})
        prep_ids = entity_ids.get("prep_ids", {})

        aggregated_lessons = {}
        rasp18_entries = []

        for group_title, schedule_result in data.items():
            if (
                entity_ids
                and "group_ids" in entity_ids
                and group_title in entity_ids["group_ids"]
            ):
                group_id = entity_ids["group_ids"][group_title]
            else:
                group_id = await get_or_create_group(
                    self.db_session, group_title, False
                )

            for week_number, week_schedule in schedule_result.week_schedules.items():
                for weekday_str, pairs_data in week_schedule.weekday_schedules.items():
                    weekday = WEEKDAY_MAP.get(weekday_str, 0)

                    day = next(
                        (
                            d
                            for d in days
                            if d.week == week_number and d.weekday == weekday
                        ),
                        None,
                    )
                    if not day:
                        continue

                    for pair_slot, lesson_data in pairs_data.items():
                        pair = parse_pair_number(pair_slot)
                        if pair is None or not lesson_data.subject:
                            continue

                        if lesson_data.subject not in disc_ids:
                            disc_ids[lesson_data.subject] = await get_or_create_disc(
                                self.db_session, lesson_data.subject, False
                            )
                        disc_id = disc_ids[lesson_data.subject]

                        worktype = lesson_data.lesson_type_id or 0

                        agg_key = (day.id, pair, disc_id, worktype)

                        if agg_key not in aggregated_lessons:
                            timestart, timeend = get_pair_time(pair)
                            rasp18 = ScRasp18(
                                semcode=semcode,
                                day_id=day.id,
                                pair=pair,
                                kind=0,
                                worktype=worktype,
                                disc_id=disc_id,
                                timestart=timestart,
                                timeend=timeend,
                            )
                            rasp18_entries.append(rasp18)
                            entry_idx = len(rasp18_entries) - 1

                            aggregated_lessons[agg_key] = {
                                "entry_idx": entry_idx,
                                "groups": set(),
                                "rooms": set(),
                                "preps": set(),
                            }

                        aggregated_lessons[agg_key]["groups"].add(group_id)

                        if lesson_data.room:
                            rooms = parse_csv_value(lesson_data.room)
                            for room in rooms:
                                aggregated_lessons[agg_key]["rooms"].add(room)

                        if lesson_data.teacher:
                            teachers = parse_csv_value(lesson_data.teacher)
                            for teacher in teachers:
                                if teacher not in prep_ids:
                                    prep_ids[teacher] = await get_or_create_prep(
                                        self.db_session, teacher, False
                                    )
                                prep_id = prep_ids[teacher]
                                aggregated_lessons[agg_key]["preps"].add(prep_id)

        all_related = []

        if rasp18_entries:
            saved_entries = await self.repo.create_18week_schedule_entries(
                rasp18_entries
            )

            for agg_key, agg_data in aggregated_lessons.items():
                entry_idx = agg_data["entry_idx"]

                for group_id in agg_data["groups"]:
                    all_related.append(
                        ScRasp18Groups(
                            rasp18_id=rasp18_entries[entry_idx].id, group_id=group_id
                        )
                    )

                for room in agg_data["rooms"]:
                    room_value = room
                    if is_official and not room.endswith(OFFICIAL_MARKER):
                        room_value = f"{room}{OFFICIAL_MARKER}"
                    all_related.append(
                        ScRasp18Rooms(
                            rasp18_id=rasp18_entries[entry_idx].id, room=room_value
                        )
                    )

                for prep_id in agg_data["preps"]:
                    all_related.append(
                        ScRasp18Preps(
                            rasp18_id=rasp18_entries[entry_idx].id, prep_id=prep_id
                        )
                    )

            await self.repo.create_18week_relations(all_related)
            await self.db_session.commit()

    async def create_single_lesson(
        self,
        semcode: int,
        day_id: int,
        pair: int,
        kind: int,
        worktype: int,
        disc_id: int,
        group_ids: List[int],
        prep_ids: List[int],
        rooms: List[str],
        datestr: str,
    ) -> LessonInfoModel:
        """
        Создает одно занятие с проверкой конфликтов
        """
        await self.validate_lesson_conflicts(
            semcode, day_id, pair, group_ids, prep_ids, rooms
        )

        timestart, timeend = get_pair_time(pair)

        lesson_data = {
            "semcode": semcode,
            "day_id": day_id,
            "pair": pair,
            "kind": kind,
            "worktype": worktype,
            "disc_id": disc_id,
            "timestart": timestart,
            "timeend": timeend,
        }

        rasp18 = await self.repo.create_lesson(lesson_data)

        await self.repo.create_lesson_relations(
            rasp18.id, group_ids=group_ids, prep_ids=prep_ids, rooms=rooms
        )

        disc = await get_entity_by_field(self.db_session, ScDisc, "id", disc_id)

        groups = []
        for group_id in group_ids:
            group = await get_entity_by_field(self.db_session, ScGroup, "id", group_id)
            if group:
                groups.append(group.title)

        teachers = []
        for prep_id in prep_ids:
            prep = await get_entity_by_field(self.db_session, ScPrep, "id", prep_id)
            if prep:
                teachers.append(prep.fio)
        await self.db_session.commit()
        return LessonInfoModel(
            id=rasp18.id,
            day=datestr,
            pair=pair,
            disc=disc.title if disc else "",
            groups=groups,
            teachers=teachers,
            rooms=rooms,
        )

    async def move_lesson(
        self,
        lesson_id: int,
        target_date: str,
        target_pair: int,
        reason: str = "",
        comment: str = "",
    ) -> Dict[str, Any]:
        """
        Создает перенос пары на другую дату/время
        """
        src_lesson = await self.repo.get_lesson_with_related(lesson_id)
        if not src_lesson:
            raise ValueError(f"Пара с ID {lesson_id} не найдена")

        target_day = await self.repo.get_day_by_date(src_lesson.semcode, target_date)
        if not target_day:
            raise ValueError(f"День с датой {target_date} не найден")

        group_ids = [g.group_id for g in src_lesson.groups]
        prep_ids = [p.prep_id for p in src_lesson.preps]
        rooms = [r.room for r in src_lesson.rooms]

        await self.validate_lesson_conflicts(
            src_lesson.semcode, target_day.id, target_pair, group_ids, prep_ids, rooms
        )

        timestart, timeend = get_pair_time(target_pair)
        new_lesson_data = {
            "semcode": src_lesson.semcode,
            "day_id": target_day.id,
            "pair": target_pair,
            "kind": src_lesson.kind,
            "worktype": src_lesson.worktype,
            "disc_id": src_lesson.disc_id,
            "timestart": timestart,
            "timeend": timeend,
        }

        new_lesson = await self.repo.create_lesson(new_lesson_data)

        await self.repo.copy_lesson_relations(src_lesson.id, new_lesson.id)

        move_data = {
            "rasp18_dest_id": new_lesson.id,
            "src_day_id": src_lesson.day_id,
            "src_pair": src_lesson.pair,
            "reason": reason,
            "comment": comment,
        }

        await self.repo.create_lesson_move(move_data)

        await self.repo.delete_lesson(src_lesson.id)

        return {
            "source": {
                "id": lesson_id,
                "day": src_lesson.day.day.isoformat() if src_lesson.day else None,
                "pair": src_lesson.pair,
            },
            "destination": {
                "id": new_lesson.id,
                "day": target_date,
                "pair": target_pair,
            },
            "reason": reason,
            "comment": comment,
        }

    async def format_schedule_response(
        self,
        semcode: int,
        days: List[ScRasp18Days],
        entries: List[ScRasp18],
        entity_name: str,
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Форматирует данные расписания для API-ответа
        """
        day_id_to_date = {d.id: d.day for d in days}

        result = {entity_name: {}}

        for entry in entries:
            current_date = day_id_to_date[entry.day_id].isoformat()

            if current_date not in result[entity_name]:
                result[entity_name][current_date] = {}

            disc = entry.discipline.title if entry.discipline else None
            teacher_fios = [p.prep.fio for p in entry.preps if p.prep]
            rooms = [r.room for r in entry.rooms if r.room]
            groups_titles = [g.group.title for g in entry.groups if g.group]

            from core.settings.app_config import settings

            lesson_type_id = entry.worktype
            lesson_type = next(
                (
                    type_name
                    for type_name, type_id in settings.LESSON_TYPES.items()
                    if type_id == lesson_type_id
                ),
                "-",
            )

            result[entity_name][current_date][str(entry.pair)] = {
                "subject": disc,
                "teacher": ", ".join(teacher_fios) if teacher_fios else None,
                "lessonId": entry.id,
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

    async def find_free_slots(
        self,
        semcode: int,
        date_from: date,
        date_to: date,
        filter_types: List[str],
        filter_values: List[str],
    ) -> Dict[str, Dict[str, List[int]]]:
        """
        Находит свободные слоты в расписании
        """
        days = await self.repo.get_days_in_range(semcode, date_from, date_to)
        day_ids = [d.id for d in days]

        schedules = {}
        for i, filter_type in enumerate(filter_types):
            filter_value = filter_values[i]
            entries = await self.repo.get_schedule_for_entity(
                day_ids, filter_type, filter_value
            )

            schedule_data = await self.format_schedule_response(
                semcode, days, entries, filter_value
            )
            schedules[filter_value] = schedule_data.get(filter_value, {})

        result = {}
        for day in days:
            date_str = day.day.isoformat()
            result[date_str] = {}

            for entity, schedule in schedules.items():
                all_pairs = list(range(1, 8))
                busy_pairs = []

                if date_str in schedule:
                    busy_pairs = [int(pair) for pair in schedule[date_str].keys()]

                free_pairs = [p for p in all_pairs if p not in busy_pairs]
                result[date_str][entity] = free_pairs

        return result

    async def import_schedule(
        self,
        semcode: int,
        version: int,
        data: Dict[str, ScheduleResult],
        is_official: bool = False,
    ) -> ScheduleImportResultModel:
        """
        Импортирует расписание из стандартизированного содержимого
        """
        if not data:
            raise ValueError("Данные расписания отсутствуют")

        entity_ids = await self.process_7day_schedule_data(data, is_official)

        group_ids = list(entity_ids["group_ids"].values())

        await self.repo.delete_7day_schedule(semcode, version, group_ids)

        rasp7_entries, relations_data = await self.create_7day_schedule(
            semcode, version, data, entity_ids
        )

        saved_entries = await self.repo.create_7day_schedule_entries(rasp7_entries)
        relations = await self.prepare_7day_relations(
            saved_entries, relations_data, is_official
        )
        await self.repo.create_7day_relations(relations)

        await self.generate_18week_schedule(semcode, data, entity_ids, is_official)

        imported_groups = []
        for group_title in entity_ids["group_ids"].keys():
            imported_groups.append(group_title)

        return ScheduleImportResultModel(
            semcode=semcode,
            version=version,
            imported_groups=imported_groups,
            total_groups=len(imported_groups),
            is_official=is_official,
        )
