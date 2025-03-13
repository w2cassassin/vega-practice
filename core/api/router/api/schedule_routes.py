from datetime import date
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.services.schedule_service import ScheduleService
from core.services.file_manager import FileManager

from .depends import get_schedule_service, get_file_manager

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/get")
async def get_schedule(
    semcode: Optional[int] = None,
    date_from: date = Query(..., description="Начальная дата расписания"),
    date_to: date = Query(..., description="Конечная дата расписания"),
    filter_type: Literal["group", "prep", "room"] = Query(
        ..., description="Тип фильтра"
    ),
    filter_value: str = Query(..., description="Значение фильтра"),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:

    if not semcode:
        semcode = await schedule_service.get_current_semcode()

    return await schedule_service.get_schedule(
        semcode=semcode,
        date_from=date_from,
        date_to=date_to,
        filter_type=filter_type,
        filter_value=filter_value,
    )


@router.get("/search")
async def search_items(
    search_type: Literal["group", "prep", "room"] = Query(
        ..., description="Тип поиска"
    ),
    q: str = Query(..., description="Поисковый запрос"),
    limit: int = Query(10, description="Максимальное количество результатов"),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> list[str]:
    return await schedule_service.search_items(
        search_type=search_type, query=q, limit=limit
    )


@router.get("/info")
async def get_schedule_info(
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> Dict[str, Any]:

    return await schedule_service.get_schedule_info()


@router.get("/semester-dates")
async def get_semester_dates(
    semcode: Optional[int] = None,
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> Dict[str, Any]:

    if not semcode:
        semcode = await schedule_service.get_current_semcode()

    return await schedule_service.get_semester_dates(semcode)


@router.get("/free-slots")
async def get_free_slots(
    date_from: date,
    date_to: date,
    filter_types: List[Literal["group", "prep", "room"]] = Query(
        ..., description="Типы фильтров"
    ),
    filter_values: List[str] = Query(..., description="Значения фильтров"),
    semcode: Optional[int] = None,
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> Dict[str, Dict[str, List[int]]]:

    if not semcode:
        semcode = await schedule_service.get_current_semcode()

    if len(filter_types) != len(filter_values):
        raise HTTPException(
            status_code=400,
            detail="Количество типов фильтров должно соответствовать количеству значений",
        )

    return await schedule_service.get_free_slots(
        semcode=semcode,
        date_from=date_from,
        date_to=date_to,
        filter_types=filter_types,
        filter_values=filter_values,
    )


@router.post("/import-from-file")
async def import_from_file(
    file_id: int,
    semcode: Optional[int] = None,
    version: int = 1,
    schedule_service: ScheduleService = Depends(get_schedule_service),
    file_manager: FileManager = Depends(get_file_manager),
) -> Dict[str, Any]:
    """
    Импортирует расписание из ранее загруженного файла в базу данных
    """
    if not semcode:
        semcode = await schedule_service.get_current_semcode()

    file = await file_manager.get_file(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    try:
        if not file.standardized_content:
            raise HTTPException(
                status_code=400, detail="Файл не содержит данных расписания"
            )

        return await schedule_service.import_schedule_from_standardized_content(
            semcode=semcode,
            version=version,
            standardized_content=file.standardized_content,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при импорте расписания: {str(e)}"
        )


@router.get("/current-week")
async def get_current_week(
    semcode: Optional[int] = None,
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> Dict[str, Any]:

    if not semcode:
        semcode = await schedule_service.get_current_semcode()

    return await schedule_service.get_current_week_info(semcode)
