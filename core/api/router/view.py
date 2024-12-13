from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from core.settings.app_config import settings

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/")
async def get_index(request: Request):
    api_url = settings.API_URL
    return templates.TemplateResponse(
        "index.html", {"request": request, "api_url": api_url}
    )


@router.get("/schedule")
async def get_schedule(request: Request):
    api_url = settings.API_URL
    return templates.TemplateResponse(
        "schedule.html", {"request": request, "api_url": api_url}
    )
