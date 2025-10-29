# service/app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import AnyUrl
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Trustworthy Model Registry"
    ENV: str = "dev"
    DB_URL: str = "sqlite:///./data/registry.db"
    STORAGE_BACKEND: str = "local"
    BLOB_ROOT: str = "./data/blobs"
    S3_BUCKET: str | None = None
    AWS_REGION: str | None = None
    JWT_SECRET: str = "change-me-in-prod"
    JWT_ISSUER: str = "model-registry"
    JWT_AUDIENCE: str = "model-registry-users"
    JWT_EXPIRE_HOURS: int = 10
    JWT_MAX_CALLS: int = 1000
    GITHUB_TOKEN: str | None = None
    NODE_PATH: str = "node"
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True

from functools import lru_cache
@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file=".env", _env_file_encoding="utf-8")
