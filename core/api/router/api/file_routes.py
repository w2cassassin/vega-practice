from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from core.api.router.api.depends import (get_compare_service, get_file_manager,
                                         get_schedule_service)
from core.services.file_manager import FileManager
from core.services.schedule_compare import ScheduleCompareService
from core.services.schedule_service import ScheduleService

router = APIRouter(tags=["files"])


@router.post("/add_file/")
async def add_file(
    file: UploadFile = File(...),
    file_manager: FileManager = Depends(get_file_manager),
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    try:
        if not file.filename.endswith(".xlsx") and not file.filename.endswith(".ics"):
            raise HTTPException(status_code=400, detail="Wrong format")
        saved_file = await file_manager.save_file(file)
        await schedule_service.add_or_update_7day_schedule_from_dict(
            1, 1, saved_file.standardized_content
        )

        file_id = saved_file.id

        return {
            "id": file_id,
            "name": file.filename,
            "created_at": saved_file.created_at,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files/")
async def all_files(file_manager: FileManager = Depends(get_file_manager)):
    try:
        files = await file_manager.list_files()
        return {
            "files": [
                {
                    "name": file.original_name,
                    "id": file.id,
                    "created_at": file.created_at,
                    "standardized_content": file.standardized_content,
                }
                for file in files
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete_file/{file_id}")
async def delete_file(
    file_id: int, file_manager: FileManager = Depends(get_file_manager)
):
    try:
        await file_manager.delete_file(file_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Файл успешно удален"}


@router.get("/download_file/{file_id}")
async def download_file(
    file_id: int, file_manager: FileManager = Depends(get_file_manager)
):
    try:
        file_data = await file_manager.get_file(file_id)
        await file_manager.delete_file(file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="Файл не найден")

        filename = quote(file_data.original_name)

        headers = {
            "Content-Disposition": f"attachment; filename*=utf-8''{filename}",
        }
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        return Response(
            content=file_data.file_data, headers=headers, media_type=media_type
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/compare_files/")
async def compare_files(
    file_id_1: int,
    file_id_2: int,
    file_manager: FileManager = Depends(get_file_manager),
    compare_service: ScheduleCompareService = Depends(get_compare_service),
):
    try:
        file_1 = await file_manager.get_file(file_id_1)
        file_2 = await file_manager.get_file(file_id_2)

        if not file_1 or not file_2:
            raise HTTPException(status_code=404, detail="Файлы не найдены")

        if not file_1.standardized_content or not file_2.standardized_content:
            raise HTTPException(
                status_code=400, detail="Файлы не содержат стандартизированных данных"
            )

        result = compare_service.compare_schedules(
            file_1.standardized_content, file_2.standardized_content
        )

        return {"metadata": result}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search_groups/")
async def search_groups(match: str):
    external_api_url = "https://schedule-of.mirea.ru/schedule/api/search"
    params = {"limit": 15, "match": match}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(external_api_url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return data
