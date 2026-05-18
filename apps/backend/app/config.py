from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    alembic_database_url: str
    artifact_storage_root: str = Field(
        default="storage",
        validation_alias=AliasChoices("ARTIFACT_STORAGE_ROOT", "STORAGE_PATH"),
    )
    internal_service_token: str = ""

settings = Settings()
