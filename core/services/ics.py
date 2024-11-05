import datetime
from io import BytesIO
from typing import Dict

from icalendar import Calendar, Event

WEEKDAYS = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]


class IcsCompareService:
    def __init__(self, group_name=None):
        self.main_calendar = None
        self.group_name = group_name

    def load(self, calendar_file):
        if isinstance(calendar_file, (bytes, BytesIO)):
            content = (
                calendar_file.read()
                if isinstance(calendar_file, BytesIO)
                else calendar_file
            )
            self.main_calendar = Calendar.from_ical(content)
        else:
            with open(calendar_file, "rb") as f:
                self.main_calendar = Calendar.from_ical(f.read())
        if not self.group_name:
            self.group_name = self._get_calendar_name()

    def compare(self, file_to_compare):
        if self.main_calendar is None:
            raise ValueError("Main calendar not loaded.")

        if isinstance(file_to_compare, (bytes, BytesIO)):
            content = (
                file_to_compare.read()
                if isinstance(file_to_compare, BytesIO)
                else file_to_compare
            )
            compare_calendar = Calendar.from_ical(content)
        else:
            with open(file_to_compare, "rb") as f:
                compare_calendar = Calendar.from_ical(f.read())

        main_events = self._build_event_dict(self.main_calendar)
        compare_events = self._build_event_dict(compare_calendar)

        compare_data = {"title": 0, "fio": 0, "room": 0, "campus": 0, "changes": {}}

        for event_key, main_event in main_events.items():
            if event_key in compare_events:
                compare_event = compare_events[event_key]
                self._compare_events(main_event, compare_event, compare_data)
            else:
                self._record_missing_event(
                    main_event, compare_data, missing_in="в первом"
                )

        for event_key, compare_event in compare_events.items():
            if event_key not in main_events:
                self._record_missing_event(
                    compare_event, compare_data, missing_in="во втором"
                )

        return compare_data

    def _build_event_dict(self, calendar):
        events_dict = {}
        for component in calendar.walk():
            if component.name == "VEVENT":
                key = component.get("UID")
                events_dict[key] = component
        return events_dict

    def _compare_events(self, event1, event2, compare_data: Dict):
        group_name = self.group_name
        dtstart = event1.get("DTSTART").dt
        if not isinstance(dtstart, datetime.datetime):
            return
        weekday_num = dtstart.weekday()
        weekday = WEEKDAYS[weekday_num]
        lesson_num = self._get_lesson_num(dtstart.time())

        changes = []

        if event1.get("SUMMARY") != event2.get("SUMMARY"):
            compare_data["title"] += 1
            changes.append(f"{event1.get('SUMMARY')} -> {event2.get('SUMMARY')}")

        fio1 = self._extract_teacher_name(event1.get("DESCRIPTION"))
        fio2 = self._extract_teacher_name(event2.get("DESCRIPTION"))
        if fio1 != fio2:
            compare_data["fio"] += 1
            changes.append(f"{fio1} -> {fio2}")

        room1 = self._extract_room(event1.get("LOCATION"))
        room2 = self._extract_room(event2.get("LOCATION"))
        if room1 != room2:
            compare_data["room"] += 1
            changes.append(f"{room1} -> {room2}")

        campus1 = self._extract_campus(event1.get("LOCATION"))
        campus2 = self._extract_campus(event2.get("LOCATION"))
        if campus1 != campus2:
            compare_data["campus"] += 1
            changes.append(f"{campus1} -> {campus2}")

        if changes:
            if group_name not in compare_data["changes"]:
                compare_data["changes"][group_name] = {}
            if weekday not in compare_data["changes"][group_name]:
                compare_data["changes"][group_name][weekday] = {}
            if lesson_num not in compare_data["changes"][group_name][weekday]:
                compare_data["changes"][group_name][weekday][lesson_num] = []
            compare_data["changes"][group_name][weekday][lesson_num].extend(changes)

    def _record_missing_event(self, event, compare_data: Dict, missing_in: str):
        group_name = self.group_name
        weekday_num = event.get("DTSTART").dt.weekday()
        weekday = WEEKDAYS[weekday_num]
        lesson_num = self._get_lesson_num(event.get("DTSTART").dt.time())

        if group_name not in compare_data["changes"]:
            compare_data["changes"][group_name] = {}

        if weekday not in compare_data["changes"][group_name]:
            compare_data["changes"][group_name][weekday] = {}

        if lesson_num not in compare_data["changes"][group_name][weekday]:
            compare_data["changes"][group_name][weekday][lesson_num] = []

        message = f"Пара найдена только {missing_in} файле: {event.get('SUMMARY')}"
        compare_data["changes"][group_name][weekday][lesson_num].append(message)

    def _extract_teacher_name(self, description):
        if description:
            lines = description.split("\n")
            for line in lines:
                if line.startswith("Преподаватель:"):
                    return line.replace("Преподаватель:", "").strip()
        return ""

    def _extract_room(self, location):
        if location:
            parts = location.split(" ")
            if parts:
                return parts[0].strip()
        return location

    def _extract_campus(self, location):
        if location:
            parts = location.split(" ")
            if parts:
                return parts[1].strip()
        return location

    def _get_lesson_num(self, event_start_time):
        time_to_lesson = {
            datetime.time(9, 00): 1,
            datetime.time(10, 40): 2,
            datetime.time(12, 40): 3,
            datetime.time(14, 20): 4,
            datetime.time(16, 20): 5,
            datetime.time(18, 00): 6,
            datetime.time(19, 40): 7,
        }
        for time_obj, lesson_num in time_to_lesson.items():
            if event_start_time == time_obj:
                return lesson_num
        return 0

    def _get_calendar_name(self):
        return str(self.main_calendar.get("X-WR-CALNAME"))
