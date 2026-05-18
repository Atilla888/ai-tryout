from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Monorepo root (ai-spaces/) — .env lives next to docker-compose.yml
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            _REPO_ROOT / ".env",
            _BACKEND_ROOT / ".env",
            ".env",
        ),
        extra="ignore",
    )

    database_url: str
    alembic_database_url: str
    artifact_storage_root: str = Field(
        default="storage",
        validation_alias=AliasChoices("ARTIFACT_STORAGE_ROOT", "STORAGE_PATH"),
    )
    internal_service_token: str = ""

settings = Settings()
