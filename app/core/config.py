from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pydantic import field_validator
from typing import Union

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 2

    FRONTEND_URLS: Union[list[str], str] = ["http://localhost:5173"]

    #runs implicitly before model initialization
    @field_validator('FRONTEND_URLS', mode='before')
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(',')]
        return v

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()