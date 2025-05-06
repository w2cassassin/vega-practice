from abc import ABC, abstractmethod
from typing import Dict, List
from datetime import datetime, timedelta

from core.schemas.schedule import LessonData, WeekSchedule, ScheduleResult
from core.utils.maps import WEEKDAYS


class BaseConverter(ABC):
    """Базовый абстрактный класс для конвертеров расписания"""

    def __init__(self):
        self.total_weeks = 18  # Количество недель в семестре
        self.start_of_semester = None  # Дата начала семестра

    @abstractmethod
    def convert(self, file_data: bytes) -> ScheduleResult:
        """Конвертирование файла в стандартный формат расписания"""
        pass

    def _convert_full_name(self, full_name: str) -> str:
        """Конвертирует ФИО в сокращенный формат"""
        if not full_name:
            return ""
        parts = full_name.split()
        if len(parts) >= 3:
            return f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
        return full_name

    def _get_week_number(self, date: datetime) -> int:
        """Определить номер недели относительно start_of_semester"""
        if not self.start_of_semester:
            return 1

        delta = date.date() - self.start_of_semester.date()
        return delta.days // 7 + 1  # Номер недели (начиная с 1)

    def _create_week_schedule(self, week_number: int) -> WeekSchedule:
        """Создать структуру расписания для конкретной недели"""
        return WeekSchedule(
            week_number=week_number,
            weekday_schedules={weekday: {} for weekday in WEEKDAYS},
        )

    def _add_lesson_to_schedule(
        self,
        result: ScheduleResult,
        week_number: int,
        weekday: str,
        lesson_num: str,
        lesson_data: LessonData,
    ):
        """Добавить занятие в расписание на конкретную неделю"""
        if week_number not in result.week_schedules:
            result.week_schedules[week_number] = self._create_week_schedule(week_number)

        if weekday not in result.week_schedules[week_number].weekday_schedules:
            result.week_schedules[week_number].weekday_schedules[weekday] = {}

        result.week_schedules[week_number].weekday_schedules[weekday][
            lesson_num
        ] = lesson_data
