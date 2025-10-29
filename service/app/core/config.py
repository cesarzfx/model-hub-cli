# service/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # General
    ENV: str = "dev"
    APP_NAME: str = "Trustworthy Model Registry"

    # Storage / DB
    DB_URL: str = "sqlite:///./data/registry/db"   # matches earlier examples
    STORAGE_BACKEND: str = "local"
    BLOB_ROOT: str = "./data/blobs"
    S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"

    # Auth (defaults match the .env you’ve been using)
    JWT_SECRET: str = "dev-secret-please-change"
    JWT_ISSUER: str = "model-hub-cli"
    JWT_AUDIENCE: str = "model-hub-cli-users"
    JWT_EXPIRE_HOURS: int = 24
    JWT_MAX_CALLS: int = 1000

    # Optional GitHub token for Reviewedness metric
    GITHUB_TOKEN: str = ""

    # Misc
    NODE_PATH: str = "node"
    MAX_PAGE_SIZE: int = 100

    # IMPORTANT: use v2 config style so .env is loaded
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
