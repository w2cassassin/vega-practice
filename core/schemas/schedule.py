from typing import Dict, List, Optional, Union, Any
from datetime import date
from pydantic import BaseModel as PydanticBaseModel, RootModel

from core.schemas.base import BaseModel


class LessonData(BaseModel):
    """Модель данных о занятии"""

    subject: str = ""
    teacher: str = ""
    room: str = ""
    campus: str = ""
    lesson_type: str = ""
    lesson_type_id: Optional[Union[str, int]] = None
    date: Optional[str] = None


class WeekSchedule(BaseModel):
    """Модель расписания на конкретную неделю"""

    week_number: int
    weekday_schedules: Dict[str, Dict[str, LessonData]] = {}


class ScheduleResult(BaseModel):
    """Результат конвертации файла с расписанием"""

    group_name: str = ""
    week_schedules: Dict[int, WeekSchedule] = {}


# Модели для API-ответов


class ScheduleResponseModel(RootModel):
    """Ответ API с расписанием"""

    root: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]


class DayInfoModel(BaseModel):
    """Информация о дне семестра"""

    date: str
    weekday: int
    weekday_name: str
    week: int
    is_odd_week: bool


class SemesterDatesModel(BaseModel):
    """Информация о датах семестра"""

    semcode: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    days: List[DayInfoModel] = []


class VersionInfoModel(BaseModel):
    """Информация о версии расписания"""

    semcode: int
    version: int
    imported_groups: List[str] = []
    total_groups: int
    is_official: bool


class CurrentWeekInfoModel(BaseModel):
    """Информация о текущей неделе"""

    week_number: Optional[int] = None
    is_odd_week: Optional[bool] = None
    week_start: Optional[str] = None
    week_end: Optional[str] = None
    current_day: str
    status: Optional[str] = None


class LessonTypeModel(BaseModel):
    """Тип занятия"""

    id: str
    name: str


class ScheduleInfoModel(BaseModel):
    """Информация о расписании"""

    current_semcode: int
    semcodes: List[int] = []
    versions_by_semcode: Dict[str, List[int]] = {}
    semester_dates: Dict[str, Dict[str, Optional[str]]] = {}
    lesson_types: Dict[str, str] = {}


class LessonCreateRequest(BaseModel):
    """Запрос на создание занятия"""

    semcode: int
    date: str
    pair: int
    kind: int = 0
    worktype: int
    disc_title: str
    group_titles: List[str]
    prep_fios: List[str]
    rooms: List[str]
    is_official: bool = False
    weeks: Optional[List[int]] = None


class LessonMoveRequest(BaseModel):
    """Запрос на перенос занятия"""

    lesson_id: int
    target_date: str
    target_pair: int
    reason: str = ""
    comment: str = ""


class LessonInfoModel(BaseModel):
    """Информация о занятии"""

    id: int
    day: str
    pair: int
    disc: str
    groups: List[str] = []
    teachers: List[str] = []
    rooms: List[str] = []


class ScheduleImportResultModel(BaseModel):
    """Результат импорта расписания"""

    semcode: int
    version: int
    imported_groups: List[str] = []
    total_groups: int
    is_official: bool


# Модели для результатов сравнения расписаний


class LessonDetailsCompareModel(BaseModel):
    """Детали занятия для сравнения"""

    subject: str = "—"
    teacher: str = "—"
    room: str = "—"
    campus: str = "—"


class LessonChangeModel(BaseModel):
    """Модель изменения в занятии"""

    field: str
    from_value: str
    to_value: str


class WeekComparisonItemModel(BaseModel):
    """Сравнение занятия на конкретной неделе"""

    week: int
    before: Optional[LessonDetailsCompareModel] = None
    after: Optional[LessonDetailsCompareModel] = None
    change_type: str = "unchanged"  # "unchanged", "added", "removed", "modified"
    changed_fields: List[str] = []


class AddedLessonModel(BaseModel):
    """Модель добавленного занятия"""

    day: str
    lesson: str
    details: LessonDetailsCompareModel
    week: int
    weeks_comparison: List[WeekComparisonItemModel] = []


class RemovedLessonModel(BaseModel):
    """Модель удаленного занятия"""

    day: str
    lesson: str
    details: LessonDetailsCompareModel
    week: int
    weeks_comparison: List[WeekComparisonItemModel] = []


class ModifiedLessonModel(BaseModel):
    """Модель измененного занятия"""

    day: str
    lesson: str
    changes: List[LessonChangeModel]
    before: LessonDetailsCompareModel
    after: LessonDetailsCompareModel
    week: int
    weeks_comparison: List[WeekComparisonItemModel] = []


class ScheduleChangeDetailsModel(BaseModel):
    """Детали изменений в расписании"""

    added: List[AddedLessonModel] = []
    removed: List[RemovedLessonModel] = []
    modified: List[ModifiedLessonModel] = []


class ChangeSummaryModel(BaseModel):
    """Сводка изменений по типам"""

    subject: int = 0
    teacher: int = 0
    room: int = 0
    campus: int = 0


class GroupComparisonModel(BaseModel):
    """Результат сравнения для группы"""

    total: int = 0
    details: ScheduleChangeDetailsModel = ScheduleChangeDetailsModel()
    summary: ChangeSummaryModel = ChangeSummaryModel()


class ScheduleComparisonResultModel(BaseModel):
    """Полный результат сравнения расписаний"""

    groups: Dict[str, GroupComparisonModel] = {}
