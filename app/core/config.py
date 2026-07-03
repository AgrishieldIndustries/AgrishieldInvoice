import json
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict

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
            url = self.DATABASE_URL
            # Ensure asyncpg driver is used
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        # Default to local SQLite fallback
        if (self.POSTGRES_SERVER == "localhost"
                and self.POSTGRES_PASSWORD == "postgres"
                and self.POSTGRES_USER == "postgres"):
            return "sqlite+aiosqlite:///./agrishield.db"
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # CORS — stored as raw string, parsed via property to support both formats:
    #   JSON array:        '["https://example.com","http://localhost:3000"]'
    #   Comma-separated:   'https://example.com,http://localhost:3000'
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        v = self.BACKEND_CORS_ORIGINS.strip()
        # Try JSON array first
        if v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(i).strip() for i in parsed if i]
            except json.JSONDecodeError:
                pass
        # Fall back to comma-separated
        return [i.strip() for i in v.split(",") if i.strip()]


settings = Settings()
