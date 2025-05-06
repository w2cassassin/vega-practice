from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(override=True)


class Settings(BaseSettings):
    class Config:
        case_sensitive = True

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    ROOT_PATH: str
    BASE_HOST: str = "https://vega.mirea.ru"

    @property
    def BASE_URL(self) -> str:
        return f"{self.BASE_HOST}{self.ROOT_PATH}"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"""postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"""

    LESSON_TYPES: dict = {
        "ПР": 0,
        "ЛК": 1,
        "ЛАБ": 2,
        "ЭКЗ": 11,
        "ЗАЧ": 12,
        "ЗАЧ-Д": 13,
        "КР": 14,
        "КП": 15,
        "СР": 16,
        "КОНС": 17,
    }


settings = Settings()
