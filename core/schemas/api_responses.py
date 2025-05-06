from typing import Any, Dict, List, Optional, Union
from datetime import date

from core.schemas.base import BaseModel
from core.schemas.schedule import (
    ScheduleInfoModel,
    SemesterDatesModel,
    CurrentWeekInfoModel,
    LessonInfoModel,
    ScheduleComparisonResultModel,
)


class FileResponseModel(BaseModel):
    """Модель ответа с информацией о файле"""

    id: int
    name: str
    created_at: str
    is_official: bool = False
    group_count: Optional[int] = None
    group_names: Optional[List[str]] = None


class FileListResponseModel(BaseModel):
    """Модель списка файлов"""

    files: List[FileResponseModel]


class MessageResponseModel(BaseModel):
    """Модель для простых ответов с сообщением"""

    message: str


class GroupListResponseModel(BaseModel):
    """Модель списка групп"""

    groups: List[str]


class ExternalGroupModel(BaseModel):
    """Модель группы из внешнего API"""

    fullTitle: str
    iCalLink: Optional[str] = None
    id: Optional[int] = None


class ExternalGroupsResponseModel(BaseModel):
    """Модель ответа от внешнего API с группами"""

    data: List[ExternalGroupModel]


class ImportResultResponseModel(BaseModel):
    """Модель результата импорта расписания"""

    id: int
    name: str
    created_at: str
    group_count: int
    imported_to_db: bool
    semcode: int
    is_official: bool


class LessonMoveResponseModel(BaseModel):
    """Модель ответа при переносе пары"""

    source: Dict[str, Any]
    destination: Dict[str, Any]
    reason: str
    comment: str


class LessonCreateMultipleResponseModel(BaseModel):
    """Модель ответа при создании нескольких пар"""

    created_lessons: List[LessonInfoModel]
    errors: List[Dict[str, Any]]
    total_created: int
    total_errors: int


class GroupDownloadResponseModel(BaseModel):
    """Модель ответа при скачивании расписаний групп"""

    id: int
    name: str
    created_at: str
    group_count: int
    imported_to_db: bool
    semcode: int
    is_official: bool
