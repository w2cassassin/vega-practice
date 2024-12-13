from datetime import date
from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends

from core.services.schedule_service import ScheduleService

from .depends import get_schedule_service

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/get")
async def get_schedule(
    semcode: int,
    date_from: date,
    date_to: date,
    filter_type: Literal["group", "prep", "room"],
    filter_value: str,
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
    return await schedule_service.get_schedule(
        semcode=semcode,
        date_from=date_from,
        date_to=date_to,
        filter_type=filter_type,
        filter_value=filter_value,
    )


@router.get("/search")
async def search_items(
    search_type: Literal["group", "prep", "room"],
    q: str,
    limit: int = 10,
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> list[str]:
    return await schedule_service.search_items(
        search_type=search_type, query=q, limit=limit
    )
