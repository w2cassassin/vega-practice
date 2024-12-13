from fastapi import APIRouter

from core.api.router.api.file_routes import router as files_router
from core.api.router.api.schedule_routes import router as schedule_router
from core.api.router.view import router as main_router

router = APIRouter()

api_router = APIRouter(prefix="/api")
api_router.include_router(files_router)
api_router.include_router(schedule_router)

router.include_router(api_router)
router.include_router(main_router)
