from pathlib import Path
from typing import Any

from pydantic import field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource
from pydantic_settings.sources import PydanticBaseSettingsSource


ROOT_DIR = Path(__file__).parent.parent.parent.parent


def _get_yaml_path() -> str:
    config_path = Path("/etc/bioscopeai-vision-streamer-config.yaml")
    if not config_path.exists():
        config_path = ROOT_DIR / "docs/bioscopeai-vision-streamer-config.yaml"
    return str(config_path)


class AppSettings(BaseSettings):
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    LOG_FILE_LEVEL: str = "debug"
    LOG_FILE_PATH: str = "vision_streamer.log"
    PROJECT_NAME: str = "BioScopeAI Vision Streamer"
    PROJECT_VERSION: str = "0.0.1"
    BACKEND_CORS_ORIGINS: str | list[str]
    UVICORN_ADDRESS: str
    UVICORN_PORT: int

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @staticmethod
    def split_cors_origins(v: Any) -> str | list[str] | Any:
        if isinstance(v, str) and "," in v:
            return [i.strip() for i in v.split(",")]
        return v


class SentrySettings(BaseSettings):
    SENTRY_DSN: SecretStr | None = None


class AuthSettings(BaseSettings):
    ACCESS_TOKEN_TTL_MINUTES: int = 15 * 15  # 15 minutes
    REFRESH_TOKEN_TTL_MINUTES: int = 60 * 24 * 7  # 7 days
    PUBLIC_KEY: str
    PRIVATE_KEY: SecretStr


class Settings(BaseSettings):
    app: AppSettings
    sentry: SentrySettings
    auth: AuthSettings

    model_config = SettingsConfigDict(
        yaml_file=_get_yaml_path(),
        yaml_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )


settings = Settings()
