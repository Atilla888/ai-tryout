from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    alembic_database_url: str
    artifact_storage_root: str = "storage"
    internal_service_token: str = ""

settings = Settings()