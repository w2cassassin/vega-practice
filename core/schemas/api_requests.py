from typing import Any, Dict, List, Optional, Literal
from datetime import date

from core.schemas.base import BaseModel


class GroupDownloadRequest(BaseModel):
    """Запрос на скачивание расписаний для групп"""

    groups: List[str]


class LessonAddRequest(BaseModel):
    """Запрос на добавление пары"""

    date: str
    pair: int
    kind: int = 0
    worktype: int
    subject: str
    groups: List[str]
    teachers: List[str]
    rooms: List[str]
    weeks: Optional[List[int]] = None


class LessonMoveRequest(BaseModel):
    """Запрос на перенос пары"""

    lesson_id: int
    target_date: str
    target_pair: int
    reason: str = ""
    comment: str = ""


class ImportFromFileRequest(BaseModel):
    """Запрос на импорт расписания из файла"""

    file_id: int
    semcode: Optional[int] = None
    version: int = 1
    is_official: bool = False
