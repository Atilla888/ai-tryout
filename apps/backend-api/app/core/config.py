from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://aispacesuser:aispacespass@localhost:5432/aispaces"

    # Application
    app_title: str = "AI Spaces API"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str = "changeme-in-production"

    # Storage
    storage_path: str = "/app/storage"

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
