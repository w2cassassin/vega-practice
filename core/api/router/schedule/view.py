from datetime import date
from typing import Any, Dict, List, Literal, Optional

from attr import s
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from core.repositories.file_repository import FileRepository
from core.services.schedule_service import ScheduleService
from core.services.schedule_downloader import ScheduleDownloader
from core.schemas.schedule import (
    ScheduleInfoModel,
    SemesterDatesModel,
    CurrentWeekInfoModel,
    LessonInfoModel,
    ScheduleResponseModel,
)
from core.schemas.api_responses import (
    ImportResultResponseModel,
    LessonMoveResponseModel,
    LessonCreateMultipleResponseModel,
    GroupDownloadResponseModel,
)
from core.schemas.api_requests import (
    GroupDownloadRequest,
    LessonAddRequest,
    LessonMoveRequest,
    ImportFromFileRequest,
)
from core.api.router.schedule.depends import (
    get_schedule_service,
    get_file_manager,
    get_schedule_downloader,
)

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
) -> ScheduleResponseModel:

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
    search_type: Literal["subject", "group", "prep", "room"] = Query(
        ..., description="Тип поиска"
    ),
    q: str = Query(..., description="Поисковый запрос"),
    limit: int = Query(10, description="Максимальное количество результатов"),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> List[str]:
    return await schedule_service.search_items(
        search_type=search_type, query=q, limit=limit
    )


@router.get("/info")
async def get_schedule_info(
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleInfoModel:
    return await schedule_service.get_schedule_info()


@router.get("/semester-dates")
async def get_semester_dates(
    semcode: Optional[int] = None,
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> SemesterDatesModel:

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
) -> Dict[str, Any]:

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
    request: ImportFromFileRequest,
    schedule_service: ScheduleService = Depends(get_schedule_service),
    file_manager: FileRepository = Depends(get_file_manager),
) -> ImportResultResponseModel:
    """
    Импортирует расписание из ранее загруженного файла в базу данных
    """
    semcode = request.semcode
    if not semcode:
        semcode = await schedule_service.get_current_semcode()

    file = await file_manager.get_file(request.file_id)
    if not file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    try:
        if not file.standardized_content:
            raise HTTPException(
                status_code=400, detail="Файл не содержит данных расписания"
            )

        result = await schedule_service.import_schedule_from_standardized_content(
            semcode=semcode,
            version=request.version,
            standardized_content=file.standardized_content,
            is_official=request.is_official,
        )

        return ImportResultResponseModel(
            id=request.file_id,
            name=file.original_name,
            created_at=file.created_at.isoformat(),
            group_count=result.total_groups,
            imported_to_db=True,
            semcode=semcode,
            is_official=request.is_official,
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
) -> CurrentWeekInfoModel:

    if not semcode:
        semcode = await schedule_service.get_current_semcode()

    return await schedule_service.get_current_week_info(semcode)


@router.post("/add-lesson")
async def add_lesson(
    request: LessonAddRequest,
    is_official: bool = False,
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> LessonInfoModel | LessonCreateMultipleResponseModel:
    """
    Добавляет новую пару в расписание
    """
    semcode = await schedule_service.get_current_semcode()

    try:
        result = await schedule_service.add_lesson(
            semcode=semcode,
            datestr=request.date,
            pair=request.pair,
            kind=request.kind,
            worktype=request.worktype,
            disc_title=request.subject,
            group_titles=request.groups,
            prep_fios=request.teachers,
            rooms=request.rooms,
            is_official=is_official,
            weeks=request.weeks,
        )

        if isinstance(result, dict) and "created_lessons" in result:
            return LessonCreateMultipleResponseModel(**result)

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при добавлении пары: {str(e)}"
        )


@router.delete("/delete-lesson")
async def delete_lesson(
    lesson_id: int,
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    """
    Удаляет пару из расписания
    """
    await schedule_service.delete_lesson(lesson_id)
    return {"ok": True}


@router.post("/move-lesson")
async def move_lesson(
    request: LessonMoveRequest,
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> LessonMoveResponseModel:
    """
    Создает перенос пары на другую дату/время
    """
    try:
        result = await schedule_service.move_lesson(
            lesson_id=request.lesson_id,
            target_date=request.target_date,
            target_pair=request.target_pair,
            reason=request.reason,
            comment=request.comment,
        )
        return LessonMoveResponseModel(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при переносе пары: {str(e)}"
        )


@router.post("/download-schedules")
async def download_schedules(
    background_tasks: BackgroundTasks,
    request: GroupDownloadRequest,
    schedule_downloader: ScheduleDownloader = Depends(get_schedule_downloader),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    file_manager: FileRepository = Depends(get_file_manager),
) -> GroupDownloadResponseModel:
    """
    Скачивает расписания групп и импортирует их в базу данных
    """
    try:
        schedule_data = await schedule_downloader.download_group_schedules(
            request.groups
        )

        new_file = await file_manager.save_schedule_data(schedule_data)
        semcode = await schedule_service.get_current_semcode()

        async def update_database():
            try:
                await schedule_service.import_schedule_from_standardized_content(
                    semcode=semcode,
                    version=1,
                    standardized_content=schedule_data["group_schedules"],
                    is_official=True,
                )
            except Exception as e:
                print(f"Ошибка в фоновой обработке: {str(e)}")
                import traceback

                print(traceback.format_exc())

        background_tasks.add_task(update_database)

        return GroupDownloadResponseModel(
            id=new_file.id,
            name=new_file.original_name,
            created_at=new_file.created_at.isoformat(),
            group_count=new_file.group_count,
            imported_to_db=True,
            semcode=semcode,
            is_official=True,
        )

    except ValueError as e:
        print(f"Ошибка валидации при скачивании расписаний: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Общая ошибка при скачивании расписаний: {str(e)}")
        import traceback

        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Ошибка при скачивании расписаний: {str(e)}"
        )
