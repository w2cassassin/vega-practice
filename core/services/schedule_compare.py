from typing import Any, Dict, List, Optional, Set

from core.utils.maps import WEEKDAYS
from core.schemas.schedule import (
    ScheduleResult,
    WeekSchedule,
    LessonData,
    ScheduleComparisonResultModel,
    GroupComparisonModel,
    ScheduleChangeDetailsModel,
    ChangeSummaryModel,
    AddedLessonModel,
    RemovedLessonModel,
    ModifiedLessonModel,
    LessonDetailsCompareModel,
    LessonChangeModel,
    WeekComparisonItemModel,
)


class ScheduleCompareService:
    """Сервис для сравнения расписаний"""

    def compare_schedules(
        self, schedule1: Dict[str, Dict], schedule2: Dict[str, Dict]
    ) -> ScheduleComparisonResultModel:
        """
        Сравнивает два расписания и возвращает информацию о различиях.
        """
        converted_schedule1 = {}
        converted_schedule2 = {}

        for group_name, group_data in schedule1.items():
            converted_schedule1[group_name] = ScheduleResult(
                group_name=group_name,
                week_schedules=group_data,
            )

        for group_name, group_data in schedule2.items():
            converted_schedule2[group_name] = ScheduleResult(
                group_name=group_name,
                week_schedules=group_data,
            )

        result = ScheduleComparisonResultModel()
        all_groups = set(schedule1.keys()) | set(schedule2.keys())

        for group in all_groups:
            group_result = GroupComparisonModel()

            if group not in schedule1:
                group_result.total = 1
                group_result.details.added.append(
                    AddedLessonModel(
                        day="Группа отсутствует в первой версии",
                        lesson="",
                        details=LessonDetailsCompareModel(
                            subject="Группа появилась во второй версии",
                            teacher="—",
                            room="—",
                            campus="—",
                        ),
                        week=0,
                    )
                )
                result.groups[group] = group_result
                continue

            if group not in schedule2:
                group_result.total = 1
                group_result.details.removed.append(
                    RemovedLessonModel(
                        day="Группа отсутствует во второй версии",
                        lesson="",
                        details=LessonDetailsCompareModel(
                            subject="Группа была в первой версии",
                            teacher="—",
                            room="—",
                            campus="—",
                        ),
                        week=0,
                    )
                )
                result.groups[group] = group_result
                continue

            group_schedule1 = converted_schedule1[group]
            group_schedule2 = converted_schedule2[group]

            all_weeks = set(group_schedule1.week_schedules.keys()) | set(
                group_schedule2.week_schedules.keys()
            )

            lessons_tracking = {}

            for week_number in all_weeks:
                has_week_in_schedule1 = week_number in group_schedule1.week_schedules
                has_week_in_schedule2 = week_number in group_schedule2.week_schedules
                if has_week_in_schedule1 and has_week_in_schedule2:
                    week_data1 = group_schedule1.week_schedules[week_number]
                    week_data2 = group_schedule2.week_schedules[week_number]
                    self._compare_week_schedules(
                        group_result,
                        week_data1,
                        week_data2,
                        week_number,
                        lessons_tracking,
                    )

            self._process_tracked_lessons(group_result, lessons_tracking, all_weeks)

            result.groups[group] = group_result

        return result

    def _process_tracked_lessons(
        self,
        group_result: GroupComparisonModel,
        lessons_tracking: Dict[tuple, Dict],
        all_weeks: Set[int],
    ) -> None:
        """Обрабатывает отслеживаемые пары и добавляет информацию о всех неделях"""
        for modified_lesson in group_result.details.modified:
            key = (modified_lesson.day, int(modified_lesson.lesson.split()[1]))
            if key in lessons_tracking:
                lesson_tracking = lessons_tracking[key]
                weeks_comparison = []

                is_odd_week = modified_lesson.week % 2 == 1
                filtered_weeks = (
                    [w for w in sorted(all_weeks) if w % 2 == 1]
                    if is_odd_week
                    else [w for w in sorted(all_weeks) if w % 2 == 0]
                )

                for week in filtered_weeks:
                    week_info = WeekComparisonItemModel(week=week)

                    if week in lesson_tracking["weeks"]:
                        week_data = lesson_tracking["weeks"][week]
                        week_info.before = week_data.get("before")
                        week_info.after = week_data.get("after")

                        if week_data.get("before") and week_data.get("after"):
                            changed_fields = []
                            for field in ["subject", "teacher", "room", "campus"]:
                                before_value = getattr(week_data["before"], field, "—")
                                after_value = getattr(week_data["after"], field, "—")
                                if before_value != after_value:
                                    changed_fields.append(field)

                            if changed_fields:
                                week_info.change_type = "modified"
                                week_info.changed_fields = changed_fields
                            else:
                                week_info.change_type = "unchanged"
                        elif week_data.get("before") and not week_data.get("after"):
                            week_info.change_type = "removed"
                        elif not week_data.get("before") and week_data.get("after"):
                            week_info.change_type = "added"

                    weeks_comparison.append(week_info)

                modified_lesson.weeks_comparison = weeks_comparison

        for added_lesson in group_result.details.added:
            key = (added_lesson.day, int(added_lesson.lesson.split()[1]))
            if key in lessons_tracking:
                lesson_tracking = lessons_tracking[key]
                weeks_comparison = []

                is_odd_week = added_lesson.week % 2 == 1
                filtered_weeks = (
                    [w for w in sorted(all_weeks) if w % 2 == 1]
                    if is_odd_week
                    else [w for w in sorted(all_weeks) if w % 2 == 0]
                )

                for week in filtered_weeks:
                    week_info = WeekComparisonItemModel(week=week)

                    if week in lesson_tracking["weeks"]:
                        if lesson_tracking["weeks"][week].get(
                            "after"
                        ) and not lesson_tracking["weeks"][week].get("before"):
                            week_info.after = lesson_tracking["weeks"][week]["after"]
                            week_info.change_type = "added"
                        elif lesson_tracking["weeks"][week].get(
                            "after"
                        ) and lesson_tracking["weeks"][week].get("before"):
                            week_info.before = lesson_tracking["weeks"][week]["before"]
                            week_info.after = lesson_tracking["weeks"][week]["after"]
                            week_info.change_type = "unchanged"

                    weeks_comparison.append(week_info)

                added_lesson.weeks_comparison = weeks_comparison

        for removed_lesson in group_result.details.removed:
            key = (removed_lesson.day, int(removed_lesson.lesson.split()[1]))
            if key in lessons_tracking:
                lesson_tracking = lessons_tracking[key]
                weeks_comparison = []

                is_odd_week = removed_lesson.week % 2 == 1
                filtered_weeks = (
                    [w for w in sorted(all_weeks) if w % 2 == 1]
                    if is_odd_week
                    else [w for w in sorted(all_weeks) if w % 2 == 0]
                )

                for week in filtered_weeks:
                    week_info = WeekComparisonItemModel(week=week)

                    if week in lesson_tracking["weeks"]:
                        if lesson_tracking["weeks"][week].get(
                            "before"
                        ) and not lesson_tracking["weeks"][week].get("after"):
                            week_info.before = lesson_tracking["weeks"][week]["before"]
                            week_info.change_type = "removed"
                        elif lesson_tracking["weeks"][week].get(
                            "before"
                        ) and lesson_tracking["weeks"][week].get("after"):
                            week_info.before = lesson_tracking["weeks"][week]["before"]
                            week_info.after = lesson_tracking["weeks"][week]["after"]
                            week_info.change_type = "unchanged"

                    weeks_comparison.append(week_info)

                removed_lesson.weeks_comparison = weeks_comparison

    def _compare_week_schedules(
        self,
        group_result: GroupComparisonModel,
        week_data1: WeekSchedule,
        week_data2: WeekSchedule,
        week_number: int,
        lessons_tracking: Optional[Dict] = None,
    ) -> None:
        all_days = set(week_data1.weekday_schedules.keys()) | set(
            week_data2.weekday_schedules.keys()
        )

        for day in all_days:
            day_schedule1 = week_data1.weekday_schedules.get(day, {})
            day_schedule2 = week_data2.weekday_schedules.get(day, {})

            all_pairs = set(day_schedule1.keys()) | set(day_schedule2.keys())

            for pair_number in all_pairs:
                has_pair_in_schedule1 = pair_number in day_schedule1
                has_pair_in_schedule2 = pair_number in day_schedule2

                tracking_key = (day, int(pair_number))

                if (
                    lessons_tracking is not None
                    and tracking_key not in lessons_tracking
                ):
                    lessons_tracking[tracking_key] = {"changes": [], "weeks": {}}

                if not has_pair_in_schedule1 and has_pair_in_schedule2:
                    lesson_data = day_schedule2[pair_number]
                    details = LessonDetailsCompareModel(
                        subject=lesson_data.subject,
                        teacher=lesson_data.teacher,
                        room=lesson_data.room,
                        campus=lesson_data.campus,
                        lesson_type=lesson_data.lesson_type,
                    )

                    existing_added = next(
                        (
                            item
                            for item in group_result.details.added
                            if item.day == day and f"Пара {pair_number}" in item.lesson
                        ),
                        None,
                    )

                    if existing_added and (existing_added.week % 2) == (
                        week_number % 2
                    ):
                        if lessons_tracking is not None:
                            if (
                                week_number
                                not in lessons_tracking[tracking_key]["weeks"]
                            ):
                                lessons_tracking[tracking_key]["weeks"][
                                    week_number
                                ] = {}
                            lessons_tracking[tracking_key]["weeks"][week_number][
                                "after"
                            ] = details
                    else:
                        group_result.details.added.append(
                            AddedLessonModel(
                                day=day,
                                lesson=f"Пара {pair_number} (неделя {week_number})",
                                details=details,
                                week=week_number,
                            )
                        )
                        group_result.total += 1

                        if lessons_tracking is not None:
                            if (
                                week_number
                                not in lessons_tracking[tracking_key]["weeks"]
                            ):
                                lessons_tracking[tracking_key]["weeks"][
                                    week_number
                                ] = {}
                            lessons_tracking[tracking_key]["weeks"][week_number][
                                "after"
                            ] = details
                    continue

                if has_pair_in_schedule1 and not has_pair_in_schedule2:
                    lesson_data = day_schedule1[pair_number]
                    details = LessonDetailsCompareModel(
                        subject=lesson_data.subject,
                        teacher=lesson_data.teacher,
                        room=lesson_data.room,
                        campus=lesson_data.campus,
                        lesson_type=lesson_data.lesson_type,
                    )

                    existing_removed = next(
                        (
                            item
                            for item in group_result.details.removed
                            if item.day == day and f"Пара {pair_number}" in item.lesson
                        ),
                        None,
                    )

                    if existing_removed and (existing_removed.week % 2) == (
                        week_number % 2
                    ):
                        if lessons_tracking is not None:
                            if (
                                week_number
                                not in lessons_tracking[tracking_key]["weeks"]
                            ):
                                lessons_tracking[tracking_key]["weeks"][
                                    week_number
                                ] = {}
                            lessons_tracking[tracking_key]["weeks"][week_number][
                                "before"
                            ] = details
                    else:
                        group_result.details.removed.append(
                            RemovedLessonModel(
                                day=day,
                                lesson=f"Пара {pair_number} (неделя {week_number})",
                                details=details,
                                week=week_number,
                            )
                        )
                        group_result.total += 1

                        if lessons_tracking is not None:
                            if (
                                week_number
                                not in lessons_tracking[tracking_key]["weeks"]
                            ):
                                lessons_tracking[tracking_key]["weeks"][
                                    week_number
                                ] = {}
                            lessons_tracking[tracking_key]["weeks"][week_number][
                                "before"
                            ] = details
                    continue

                if has_pair_in_schedule1 and has_pair_in_schedule2:
                    lesson1 = day_schedule1[pair_number]
                    lesson2 = day_schedule2[pair_number]
                    changes = []

                    for field in [
                        "subject",
                        "teacher",
                        "room",
                        "campus",
                        "lesson_type",
                    ]:
                        value1 = getattr(lesson1, field, "—")
                        value2 = getattr(lesson2, field, "—")

                        if value1 != value2:
                            changes.append(
                                LessonChangeModel(
                                    field=field,
                                    from_value=value1,
                                    to_value=value2,
                                )
                            )
                            if field != "lesson_type":
                                current_value = getattr(group_result.summary, field)
                                setattr(group_result.summary, field, current_value + 1)

                    before_details = LessonDetailsCompareModel(
                        subject=lesson1.subject,
                        teacher=lesson1.teacher,
                        room=lesson1.room,
                        campus=lesson1.campus,
                        lesson_type=lesson1.lesson_type,
                    )
                    after_details = LessonDetailsCompareModel(
                        subject=lesson2.subject,
                        teacher=lesson2.teacher,
                        room=lesson2.room,
                        campus=lesson2.campus,
                        lesson_type=lesson2.lesson_type,
                    )

                    if changes:
                        existing_modified = next(
                            (
                                item
                                for item in group_result.details.modified
                                if item.day == day
                                and f"Пара {pair_number}" in item.lesson
                            ),
                            None,
                        )

                        if existing_modified and (existing_modified.week % 2) == (
                            week_number % 2
                        ):
                            pass
                        else:
                            group_result.details.modified.append(
                                ModifiedLessonModel(
                                    day=day,
                                    lesson=f"Пара {pair_number} (неделя {week_number})",
                                    changes=changes,
                                    before=before_details,
                                    after=after_details,
                                    week=week_number,
                                )
                            )
                            group_result.total += 1

                    if lessons_tracking is not None:
                        if week_number not in lessons_tracking[tracking_key]["weeks"]:
                            lessons_tracking[tracking_key]["weeks"][week_number] = {}
                        lessons_tracking[tracking_key]["weeks"][week_number][
                            "before"
                        ] = before_details
                        lessons_tracking[tracking_key]["weeks"][week_number][
                            "after"
                        ] = after_details

                        if changes:
                            lessons_tracking[tracking_key]["changes"].extend(changes)
