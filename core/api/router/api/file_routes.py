from urllib.parse import quote
from typing import List
from pydantic import BaseModel

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from core.services.file_manager import FileManager
from core.services.schedule_compare import ScheduleCompareService
from core.services.schedule_service import ScheduleService

from core.api.router.api.depends import (
    get_compare_service,
    get_file_manager,
    get_schedule_service,
)

router = APIRouter(tags=["files"])


class GroupDownload(BaseModel):
    groups: List[str]


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
                    "group_count": file.group_count,
                }
                for file in files
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/files/{file_id}")
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

        return result

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


@router.post("/download_groups/")
async def download_groups(
    request: GroupDownload,
    file_manager: FileManager = Depends(get_file_manager),
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    """Download schedules for multiple groups and combine them"""
    try:
        new_file = await file_manager.download_group_schedules(request.groups)

        semcode = await schedule_service.get_current_semcode()

        try:
            await schedule_service.add_or_update_7day_schedule_from_dict(
                semcode=semcode,
                version=1,
                data=new_file.standardized_content,
            )

            return {
                "id": new_file.id,
                "name": new_file.original_name,
                "created_at": new_file.created_at,
                "group_count": new_file.group_count,
                "imported_to_db": True,
                "semcode": semcode,
            }
        except Exception as import_error:
            return {
                "id": new_file.id,
                "name": new_file.original_name,
                "created_at": new_file.created_at,
                "group_count": new_file.group_count,
                "imported_to_db": False,
                "import_error": str(import_error),
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download schedules: {str(e)}"
        )


@router.get("/files/{file_id}")
async def get_file(file_id: int, file_manager: FileManager = Depends(get_file_manager)):
    try:
        file_data = await file_manager.get_file(file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="Файл не найден")

        return {
            "name": file_data.original_name,
            "id": file_data.id,
            "created_at": file_data.created_at,
            "group_count": file_data.group_count,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files/{file_id}/groups")
async def get_groups_from_file(
    file_id: int, file_manager: FileManager = Depends(get_file_manager)
):
    try:
        file_data = await file_manager.get_file(file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="Файл не найден")

        if not file_data.standardized_content:
            raise HTTPException(
                status_code=400, detail="Файл не содержит данных о группах"
            )

        groups = list(file_data.standardized_content.keys())

        return {"groups": groups}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
