from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    class Config:
        case_sensitive = True

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    AUTH_HOST: str = "https://vega.mirea.ru/"
    AUTH_URL: str = AUTH_HOST + "authservice.php?op=parsetoken&token="
    ROOT_PATH: str = "/officesvc"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"""postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"""


settings = Settings()
