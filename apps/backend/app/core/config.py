# only job is to read values from .env

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_CONFIG_FILE = Path(__file__).resolve()

# Local monorepo path:
# ai-spaces/apps/backend/app/core/config.py
# parents[4] = ai-spaces
_REPO_ROOT = _CONFIG_FILE.parents[4] if len(_CONFIG_FILE.parents) > 4 else Path.cwd()
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Reads all configuration from environment variables or the monorepo .env file.
    AUTH_PROVIDER should be 'oidc' in production; it defaults to 'dev' which bypasses
    Keycloak entirely so the app can run locally without an IdP."""
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(validation_alias=AliasChoices("DATABASE_URL"))

    alembic_database_url: str = Field(
        validation_alias=AliasChoices("ALEMBIC_DATABASE_URL")
    )

    artifact_storage_root: str = Field(
        default="storage",
        validation_alias=AliasChoices("ARTIFACT_STORAGE_ROOT", "STORAGE_PATH"),
    )

    internal_service_token: str = Field(
        default="",
        validation_alias=AliasChoices("INTERNAL_SERVICE_TOKEN"),
    )

    auth_provider: str = Field(
        default="dev",
        validation_alias=AliasChoices("AUTH_PROVIDER"),
    )

    oidc_issuer: str = Field(
        default="",
        validation_alias=AliasChoices("OIDC_ISSUER"),
    )

    oidc_jwks_url: str = Field(
        default="",
        validation_alias=AliasChoices("OIDC_JWKS_URL"),
    )

    oidc_client_id: str = Field(
        default="ai-spaces-frontend",
        validation_alias=AliasChoices("OIDC_CLIENT_ID"),
    )

    oidc_algorithm: str = Field(
        default="RS256",
        validation_alias=AliasChoices("OIDC_ALGORITHM"),
    )

    oidc_audience: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OIDC_AUDIENCE"),
    )

    oidc_verify_audience: bool = Field(
        default=False,
        validation_alias=AliasChoices("OIDC_VERIFY_AUDIENCE"),
    )


settings = Settings()
