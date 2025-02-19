from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from core.settings.app_config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def render_template(request: Request, template_name: str) -> dict:
    return templates.TemplateResponse(
        template_name, {"request": request, "base_url": settings.BASE_URL}
    )


@router.get("/")
async def render_index_page(request: Request):
    return await render_template(request, "index.html")


@router.get("/schedule")
async def render_schedule_page(request: Request):
    return await render_template(request, "schedule.html")
