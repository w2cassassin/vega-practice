from typing import Dict, Any
from core.services.content_converter import WEEKDAYS

class ScheduleCompareService:
    """Сервис для сравнения расписаний"""

    def compare_schedules(
        self, schedule1: Dict[str, Any], schedule2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сравнить два расписания и вернуть различия"""
        result = {"title": 0, "fio": 0, "room": 0, "campus": 0, "changes": {}}

        all_groups = set(schedule1.keys()) | set(schedule2.keys())

        for group in all_groups:
            if group not in schedule1:
                self._record_change(
                    result, group, None, None, "Группа отсутствует в первом файле"
                )
                continue
            if group not in schedule2:
                self._record_change(
                    result, group, None, None, "Группа отсутствует во втором файле"
                )
                continue

            self._compare_group_schedule(
                group, schedule1[group], schedule2[group], result
            )

        return result

    def _compare_group_schedule(
        self, group: str, schedule1: Dict, schedule2: Dict, result: Dict
    ) -> None:
        """Сравнить расписания для группы"""
        for day in WEEKDAYS:
            if day not in schedule1 or day not in schedule2:
                continue

            day_schedule1 = schedule1[day]
            day_schedule2 = schedule2[day]

            lesson_numbers = set(str(k) for k in day_schedule1.keys()) | set(
                str(k) for k in day_schedule2.keys()
            )

            for lesson_num in lesson_numbers:
                str_lesson_num = str(lesson_num)
                lesson1 = day_schedule1.get(str_lesson_num, {})
                lesson2 = day_schedule2.get(str_lesson_num, {})

                if not lesson1 or not lesson2:
                    if not lesson1:
                        self._record_change(
                            result,
                            group,
                            day,
                            str_lesson_num,
                            "Пара отсутствует в первом файле",
                        )
                    if not lesson2:
                        self._record_change(
                            result,
                            group,
                            day,
                            str_lesson_num,
                            "Пара отсутствует во втором файле",
                        )
                    continue

                self._compare_lesson_data(
                    group, day, str_lesson_num, lesson1, lesson2, result
                )

    def _compare_lesson_data(
        self,
        group: str,
        day: str,
        lesson_num: str,
        lesson1: Dict,
        lesson2: Dict,
        result: Dict,
    ) -> None:
        """Сравнить данные пары"""
        fields = {
            "subject": ("Предмет", "title"),
            "teacher": ("Преподаватель", "fio"),
            "room": ("Аудитория", "room"),
            "campus": ("Кампус", "campus"),
        }

        for field, (field_name, counter) in fields.items():
            value1 = lesson1.get(field)
            value2 = lesson2.get(field)
            if value1 != value2:
                result[counter] += 1
                self._record_change(
                    result,
                    group,
                    day,
                    lesson_num,
                    f"{field_name}: {value2} -> {value1}",
                )

    def _record_change(
        self,
        result: Dict,
        group: str,
        day: str | None,
        lesson_num: str | None,
        change: str,
    ) -> None:
        """Записать изменение в результат"""
        if group not in result["changes"]:
            result["changes"][group] = {}

        if day is None:
            result["changes"][group] = change
            return

        if day not in result["changes"][group]:
            result["changes"][group][day] = {}
        if lesson_num not in result["changes"][group][day]:
            result["changes"][group][day][lesson_num] = []

        result["changes"][group][day][lesson_num].append(change)
