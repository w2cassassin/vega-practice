from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(override=True)


class Settings(BaseSettings):
    class Config:
        case_sensitive = True

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    ROOT_PATH: str
    BASE_URL: str = "https://vega.mirea.ru"

    @property
    def API_URL(self) -> str:
        return f"{self.BASE_URL}{self.ROOT_PATH}/api"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"""postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"""


settings = Settings()
