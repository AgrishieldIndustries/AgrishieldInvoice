import os
from typing import List, Union, Annotated
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, BeforeValidator

def assemble_cors_origins(v: Union[str, List[str]]) -> List[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 Days

    PROJECT_NAME: str = "Agrishield Admin"
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "agrishield"
    
    DATABASE_URL: Union[str, None] = None

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        # Default to local SQLite fallback if running on default local settings without custom ENV overrides
        if self.POSTGRES_SERVER == "localhost" and self.POSTGRES_PASSWORD == "postgres" and self.POSTGRES_USER == "postgres":
            return "sqlite+aiosqlite:///./agrishield.db"
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # CORS
    BACKEND_CORS_ORIGINS: Annotated[
        List[str], BeforeValidator(assemble_cors_origins)
    ] = ["http://localhost:3000"]

settings = Settings()
