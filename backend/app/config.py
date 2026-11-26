from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Читает файл .env из папки, откуда запущен сервер (C:\Bitrix24)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_MINUTES: int = 480
    COMPANY_NAME: str = "Название компании"


settings = Settings()
