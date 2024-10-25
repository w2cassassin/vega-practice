import uvicorn

from core.settings.app_config import settings
from core.main import app

if __name__ == "__main__":
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)
