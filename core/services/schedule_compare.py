from typing import Any, Dict

from core.services.content_converter import WEEKDAYS


class ScheduleCompareService:
    """Сервис для сравнения расписаний"""

    def compare_schedules(self, schedule1, schedule2):
        result = {"groups": {}}

        all_groups = set(schedule1.keys()) | set(schedule2.keys())

        for group in all_groups:
            group_result = {
                "total": 0,
                "details": {
                    "added": [],
                    "removed": [],
                    "modified": [],
                },
                "summary": {
                    "subject": 0,
                    "teacher": 0,
                    "room": 0,
                    "campus": 0,
                },
            }

            if group not in schedule1:
                group_result["total"] = 1
                group_result["details"]["added"].append(
                    {
                        "day": "Группа отсутствует в первой версии",
                        "lesson": "",
                        "details": {
                            "subject": "Группа появилась во второй версии",
                            "teacher": "—",
                            "room": "—",
                            "campus": "—",
                        },
                    }
                )
                result["groups"][group] = group_result
                continue

            if group not in schedule2:
                group_result["total"] = 1
                group_result["details"]["removed"].append(
                    {
                        "day": "Группа отсутствует во второй версии",
                        "lesson": "",
                        "details": {
                            "subject": "Группа была в первой версии",
                            "teacher": "—",
                            "room": "—",
                            "campus": "—",
                        },
                    }
                )
                result["groups"][group] = group_result
                continue

            for day in WEEKDAYS:
                if day not in schedule1[group] or day not in schedule2[group]:
                    continue

                schedule1_lessons = schedule1[group][day]
                schedule2_lessons = schedule2[group][day]

                lessons1_set = {
                    (num, type_)
                    for num in schedule1_lessons
                    for type_ in ["odd", "even"]
                    if type_ in schedule1_lessons[num]
                }
                lessons2_set = {
                    (num, type_)
                    for num in schedule2_lessons
                    for type_ in ["odd", "even"]
                    if type_ in schedule2_lessons[num]
                }

                for num, type_ in lessons2_set - lessons1_set:
                    lesson = schedule2_lessons[num][type_]
                    group_result["details"]["added"].append(
                        {
                            "day": day,
                            "lesson": f"Пара {num} ({type_})",
                            "details": {
                                "subject": lesson.get("subject", "—"),
                                "teacher": lesson.get("teacher", "—"),
                                "room": lesson.get("room", "—"),
                                "campus": lesson.get("campus", "—"),
                            },
                        }
                    )
                    group_result["total"] += 1

                for num, type_ in lessons1_set - lessons2_set:
                    lesson = schedule1_lessons[num][type_]
                    group_result["details"]["removed"].append(
                        {
                            "day": day,
                            "lesson": f"Пара {num} ({type_})",
                            "details": {
                                "subject": lesson.get("subject", "—"),
                                "teacher": lesson.get("teacher", "—"),
                                "room": lesson.get("room", "—"),
                                "campus": lesson.get("campus", "—"),
                            },
                        }
                    )
                    group_result["total"] += 1

                common_lessons = lessons1_set & lessons2_set
                for num, type_ in common_lessons:
                    lesson1 = schedule1_lessons[num][type_]
                    lesson2 = schedule2_lessons[num][type_]
                    changes = []

                    for field in ["subject", "teacher", "room", "campus"]:
                        if lesson1.get(field) != lesson2.get(field):
                            changes.append(
                                {
                                    "field": field,
                                    "from": lesson1.get(field, "—"),
                                    "to": lesson2.get(field, "—"),
                                }
                            )
                            group_result["summary"][field] += 1

                    if changes:
                        group_result["details"]["modified"].append(
                            {
                                "day": day,
                                "lesson": f"Пара {num} ({type_})",
                                "changes": changes,
                                "before": {
                                    "subject": lesson1.get("subject", "—"),
                                    "teacher": lesson1.get("teacher", "—"),
                                    "room": lesson1.get("room", "—"),
                                    "campus": lesson1.get("campus", "—"),
                                },
                                "after": {
                                    "subject": lesson2.get("subject", "—"),
                                    "teacher": lesson2.get("teacher", "—"),
                                    "room": lesson2.get("room", "—"),
                                    "campus": lesson2.get("campus", "—"),
                                },
                            }
                        )
                        group_result["total"] += 1

            result["groups"][group] = group_result

        return result
