from io import BytesIO
from typing import Any, Dict
from urllib.parse import quote

import httpx
from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     UploadFile)
from fastapi.responses import Response

from core.api.router.excel.depends import (get_compare_service,
                                           get_file_manager, get_service)
from core.services.conveter import DataConverter
from core.services.excel import ExcelCompareService
from core.services.excel import ExcelService as Service
from core.services.file_manager import FileManager
from core.services.ics import IcsCompareService

router = APIRouter(prefix="/api")
router.tags = ["excel"]


@router.post("/update/")
async def excel_generate(
    file: UploadFile = File(...),
    dictionary: Dict[str, Any] = Depends(DataConverter()),
    service: Service = Depends(get_service),
):
    """
    Принимает таблицу и словарь в теле запроса, возвращает новую таблицу. (Обновляет по закладкам)
    """
    contents = await file.read()
    service.load(BytesIO(contents))
    service.update(dictionary)
    new_file = service.save_to_bytes()
    filename = quote(file.filename)

    headers = {
        "Content-Disposition": f"attachment; filename*=utf-8''{filename}",
    }
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return Response(content=new_file.getvalue(), headers=headers, media_type=media_type)


@router.post("/get_as_json/")
async def excel_as_json(
    file: UploadFile = File(...),
    sheet_name: str = Form(None),
    range: str = Form(None),
    service: Service = Depends(get_service),
):
    """
    Получение значений таблицы в JSON.
    """
    try:
        contents = await file.read()
        service.load(BytesIO(contents))
        return service.to_json(sheet_name=sheet_name, range=range)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/update_from_json/")
async def excel_generate_from_json(
    file: UploadFile = File(...),
    dictionary: Dict[str, Any] = Depends(DataConverter()),
    service: Service = Depends(get_service),
):
    """
    Принимает таблицу и словарь в теле запроса, возвращает новую таблицу. (Обновляет по ячейкам)
    """

    contents = await file.read()
    try:
        service.load(BytesIO(contents))
        service.from_json(dictionary)
        new_file = service.save_to_bytes()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    filename = quote(file.filename)

    headers = {
        "Content-Disposition": f"attachment; filename*=utf-8''{filename}",
    }
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return Response(content=new_file.getvalue(), headers=headers, media_type=media_type)


@router.post("/update_with_blocks/")
async def excel_update_with_blocks(
    file: UploadFile = File(...),
    dictionary: Dict[str, Any] = Depends(DataConverter()),
    service: Service = Depends(get_service),
):
    """
    Принимает таблицу и словарь в теле запроса, возвращает новую таблицу. (Обновляет по ячейкам)
    """

    contents = await file.read()
    try:
        service.load(BytesIO(contents))
        service.update_with_blocks(dictionary)
        new_file = service.save_to_bytes()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    filename = quote(file.filename)

    headers = {
        "Content-Disposition": f"attachment; filename*=utf-8''{filename}",
    }
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return Response(content=new_file.getvalue(), headers=headers, media_type=media_type)


@router.post("/add_file/")
async def add_file(
    file: UploadFile = File(...), file_manager: FileManager = Depends(get_file_manager)
):
    """Endpoint to upload a file to the database."""
    try:
        saved_file = await file_manager.save_file(file)
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
    """Эндпоинт для добавления файла в базу данных"""
    try:
        files = await file_manager.list_files()
        return {
            "files": [
                {
                    "name": file.original_name,
                    "id": file.id,
                    "created_at": file.created_at,
                }
                for file in files
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Удаление файла из базы данных
@router.delete("/delete_file/{file_id}")
async def delete_file(
    file_id: int, file_manager: FileManager = Depends(get_file_manager)
):
    """Эндпоинт для удаления файла из базы данных по ID"""
    try:
        # Удаляем файл по его ID
        await file_manager.delete_file(file_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Файл успешно удален"}


@router.post("/compare_files/")
async def compare_files(
    file_id_1: int,
    file_id_2: int,
    request: Request,
    file_manager: FileManager = Depends(get_file_manager),
):
    """Endpoint for comparing two files by their IDs and saving the result in the database."""
    try:
        # Retrieve files
        file_1 = await file_manager.get_file(file_id_1)
        file_2 = await file_manager.get_file(file_id_2)

        if not file_1 or not file_2:
            raise HTTPException(status_code=404, detail="Файлы не найдены")

        filename_1 = file_1.original_name.lower()
        filename_2 = file_2.original_name.lower()

        if filename_1.endswith(".xlsx") and filename_2.endswith(".xlsx"):
            service = ExcelCompareService()
            service.load(BytesIO(file_1.file_data))
            result = service.compare(BytesIO(file_2.file_data))

            new_file = service.save_to_bytes()

            saved_file = await file_manager.save_file_from_bytes(
                new_file,
                filename=f"comparison_{file_id_1}_vs_{file_id_2}.xlsx",
            )
            file_id = saved_file.id

            scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme)

            download_url = request.url_for(
                "download_file", file_id=file_id
            )._url.replace("http://", f"{scheme}://")

            return {
                "metadata": result,
                "comparison_file_id": file_id,
                "download_url": download_url,
            }

        elif filename_1.endswith(".ics") and filename_2.endswith(".ics"):
            service = IcsCompareService()
            service.load(BytesIO(file_1.file_data))
            result = service.compare(BytesIO(file_2.file_data))

            return {
                "metadata": result,
            }
        else:
            raise HTTPException(status_code=400, detail="Неверный формат файлов.")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download_file/{file_id}")
async def download_file(
    file_id: int, file_manager: FileManager = Depends(get_file_manager)
):
    """Эндпоинт для скачивания файла из базы данных по его ID."""
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
