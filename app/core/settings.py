from functools import lru_cache

from pydantic import ConfigDict, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Dotmac Platform Core"
    VERSION: str = "0.1.0"

    # Environment
    ENV: str = "development"
    DEBUG: bool = ENV == "development"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # Database
    DATABASE_URL: PostgresDsn

    # Redis
    REDIS_URL: RedisDsn

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(env_file=".env", case_sensitive=True)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    """
    return Settings()
