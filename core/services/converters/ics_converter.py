from typing import Dict, List
from datetime import datetime, timedelta
from dateutil import rrule as dateutil_rrule
from icalendar import Calendar

from core.settings.app_config import settings
from core.schemas.schedule import LessonData, ScheduleResult
from core.utils.maps import WEEKDAYS, TIME_TO_LESSON
from core.services.converters.base_converter import BaseConverter


class ICSConverter(BaseConverter):
    """Конвертер для ICS-файлов расписания"""

    def __init__(self):
        super().__init__()
        self.semester_start_date = None
        self.semester_end_date = None
        self.freq_map = {
            "YEARLY": dateutil_rrule.YEARLY,
            "MONTHLY": dateutil_rrule.MONTHLY,
            "WEEKLY": dateutil_rrule.WEEKLY,
            "DAILY": dateutil_rrule.DAILY,
            "HOURLY": dateutil_rrule.HOURLY,
            "MINUTELY": dateutil_rrule.MINUTELY,
            "SECONDLY": dateutil_rrule.SECONDLY,
        }

    def convert(self, file_data: bytes) -> ScheduleResult:
        """Конвертировать ICS-файл в стандартный формат"""
        cal = Calendar.from_ical(file_data)
        group_name = str(cal.get("X-WR-CALNAME"))
        event_dates = []
        semester_events = []

        result = ScheduleResult(group_name=group_name)

        for component in cal.walk():
            if component.name == "VEVENT":
                start_date = None
                if component.get("dtstart"):
                    start_date = component.get("dtstart").dt

                summary = str(component.get("summary", ""))

                if isinstance(start_date, datetime):
                    event_dates.append(start_date)

                if "неделя" in summary:
                    try:
                        week_num = int(summary.split()[0])
                        semester_events.append((start_date, week_num))
                    except (ValueError, IndexError):
                        pass

        if not event_dates:
            return ScheduleResult()

        earliest_date = min(event_dates)
        self.start_of_semester = earliest_date - timedelta(days=earliest_date.weekday())

        if semester_events:
            semester_events.sort(key=lambda x: x[1])  # Сортируем по номеру недели
            self.semester_start_date = min(date for date, _ in semester_events)
            self.semester_end_date = max(
                date for date, _ in semester_events
            ) + timedelta(days=6)

        for component in cal.walk():
            if component.name == "VEVENT":
                self._process_event(component, result)

        return result

    def _process_event(self, component, result: ScheduleResult):
        """Обработать событие и добавить его в расписание"""
        start_date = component.get("dtstart").dt
        if not isinstance(start_date, datetime):
            return

        summary = str(component.get("summary", ""))
        description = str(component.get("description", ""))
        location = str(component.get("location", ""))

        if "неделя" in summary and len(summary.split()) <= 2:
            return

        subject, lesson_type, lesson_type_id = self._extract_subject_type(summary)
        room, campus = self._extract_room_campus(location)
        teacher = self._extract_teacher(description)

        weekday = WEEKDAYS[start_date.weekday()]
        lesson_num = str(self._get_lesson_number(start_date))

        if lesson_num == "0":
            return

        occurrences = self._get_event_occurrences(component)

        for occurrence in occurrences:
            week_number = self._get_week_number(occurrence)

            if week_number < 1 or week_number > self.total_weeks:
                continue

            lesson_data = LessonData(
                subject=subject,
                teacher=teacher,
                room=room,
                campus=campus,
                lesson_type=lesson_type,
                lesson_type_id=lesson_type_id,
                date=occurrence.strftime("%Y-%m-%d"),
            )

            self._add_lesson_to_schedule(
                result, week_number, weekday, lesson_num, lesson_data
            )

    def _extract_subject_type(self, summary: str) -> tuple:
        """Извлечь название предмета и тип занятия из заголовка"""
        subject = summary
        lesson_type = "ПР"
        lesson_type_id = 0

        for type_prefix, type_id in settings.LESSON_TYPES.items():
            if summary.startswith(type_prefix):
                subject = summary[len(type_prefix) :].strip()
                lesson_type = type_prefix
                lesson_type_id = type_id
                break

        return subject, lesson_type, lesson_type_id

    def _extract_room_campus(self, location: str) -> tuple:
        """Извлечь аудитории и кампусы из строки"""
        if not location:
            return "", ""

        rooms = []
        campuses = []
        location_parts = location.split()

        i = 0
        while i < len(location_parts):
            if i < len(location_parts) and not location_parts[i].startswith("("):
                room = location_parts[i].strip()
                campus = ""

                if i + 1 < len(location_parts) and location_parts[i + 1].startswith(
                    "("
                ):
                    campus = (
                        location_parts[i + 1].strip().replace("(", "").replace(")", "")
                    )
                    i += 2
                else:
                    i += 1

                rooms.append(room)
                campuses.append(campus)
            else:
                i += 1

        return ", ".join(rooms) if rooms else "", (
            ", ".join(campuses) if campuses else ""
        )

    def _extract_teacher(self, description: str) -> str:
        """Извлечь имена преподавателей из описания и конвертировать в сокращенный формат"""
        teachers = []
        if "Преподаватель:" in description:
            full_name = description.split("Преподаватель:")[1].split("\n")[0].strip()
            teachers.append(self._convert_full_name(full_name))
        elif "Преподаватели:" in description:
            teachers_section = description.split("Преподаватели:")[1]
            if "\n\n" in teachers_section:
                teachers_section = teachers_section.split("\n\n")[0]

            teacher_lines = teachers_section.strip().split("\n")
            for teacher_name in teacher_lines:
                if teacher_name.strip():
                    teachers.append(self._convert_full_name(teacher_name.strip()))

        return ", ".join(teachers)

    def _get_lesson_number(self, start_time) -> int:
        """Конвертировать время начала в номер пары"""
        time_str = start_time.strftime("%H:%M")
        return TIME_TO_LESSON.get(time_str, 0)

    def _get_week_number(self, date: datetime) -> int:
        """Определить номер недели относительно start_of_semester"""
        if not self.start_of_semester:
            return 1

        delta = date.date() - self.start_of_semester.date()
        return delta.days // 7 + 1  # Номер недели (начиная с 1)

    def _get_event_occurrences(self, component) -> List[datetime]:
        """Получить все даты проведения занятия с учетом правил повторения и исключений"""
        start_date = component.get("dtstart").dt
        if not isinstance(start_date, datetime):
            return []

        rrule_dict = component.get("RRULE", {})
        if not rrule_dict:
            return [start_date]

        exdates = []
        if "EXDATE" in component:
            for exdate in component.get("EXDATE", []).dts:
                if isinstance(exdate, list):
                    for ex_dt in exdate:
                        if hasattr(ex_dt, "dt"):
                            exdates.append(ex_dt.dt)
                elif hasattr(exdate, "dt"):
                    exdates.append(exdate.dt)

        freq = rrule_dict.get("FREQ", ["WEEKLY"])[0]
        interval = int(rrule_dict.get("INTERVAL", [1])[0])
        until = None

        if "UNTIL" in rrule_dict:
            until_str = rrule_dict.get("UNTIL")[0]
            if isinstance(until_str, datetime):
                until = until_str
            elif isinstance(until_str, str):
                if "T" in until_str:
                    until = datetime.strptime(
                        until_str.replace("Z", ""), "%Y%m%dT%H%M%S"
                    )
                else:
                    until = datetime.strptime(until_str, "%Y%m%d")
        elif self.start_of_semester:
            until = self.start_of_semester + timedelta(days=18 * 7)

        rule_params = {
            "freq": self.freq_map.get(freq, dateutil_rrule.WEEKLY),
            "dtstart": start_date,
            "interval": interval,
        }

        if until:
            rule_params["until"] = until

        dates = list(dateutil_rrule.rrule(**rule_params))

        result = []
        for date in dates:
            if date not in exdates:
                result.append(date)

        return result
