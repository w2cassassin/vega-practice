# coding=utf-8
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.api import router
from core.settings.app_config import settings


class RootPathMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, root_path: str):
        super().__init__(app)
        self.root_path = root_path

    async def dispatch(self, request, call_next):
        if not request.url.path.startswith("/static"):
            request.scope["root_path"] = self.root_path
        return await call_next(request)


app = FastAPI(title="Excel generate/analyze")

if settings.ROOT_PATH:
    app.add_middleware(RootPathMiddleware, root_path=settings.ROOT_PATH)

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)
