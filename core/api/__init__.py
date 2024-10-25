from fastapi import APIRouter, Depends

from core.api.router.excel.view import router as excel_router
from core.api.router.view import router as main_router
from core.api.sso import get_auth

# router = APIRouter(dependencies=[Depends(get_auth)])
router = APIRouter()

router.include_router(excel_router)
router.include_router(main_router)
