from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from core.settings.app_config import settings

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/")
async def get_index(request: Request):
    scheme = request.headers.get("X-Forwarded-Proto", "http")
    api_url = f"{scheme}://{request.base_url.netloc}{settings.ROOT_PATH}/api"
    return templates.TemplateResponse(
        "index.html", {"request": request, "api_url": api_url}
    )
