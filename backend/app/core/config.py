from functools import lru_cache
from pathlib import Path
import sys

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = Field("WebToActions Backend", alias="APP_NAME")
    app_env: str = Field("development", alias="APP_ENV")
    api_prefix: str = Field("/api", alias="API_PREFIX")
    webtoactions_data_dir: Path = Field(
        Path(".webtoactions"),
        alias="WEBTOACTIONS_DATA_DIR",
    )
    frontend_dev_origin: str = Field(
        "http://127.0.0.1:5173",
        alias="FRONTEND_DEV_ORIGIN",
    )
    frontend_static_enabled: bool = Field(False, alias="FRONTEND_STATIC_ENABLED")
    frontend_dist_dir: Path = Field(
        Path("frontend/dist"),
        alias="FRONTEND_DIST_DIR",
    )
    browser_channel: str = Field("chromium", alias="BROWSER_CHANNEL")
    browser_headless: bool = Field(False, alias="BROWSER_HEADLESS")

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def target_python(self) -> str:
        return "3.11+"

    @property
    def data_dir_display(self) -> str:
        try:
            return str(self.webtoactions_data_dir.relative_to(REPO_ROOT))
        except ValueError:
            return str(self.webtoactions_data_dir)

    @property
    def runtime_python(self) -> str:
        version = sys.version_info
        return f"{version.major}.{version.minor}.{version.micro}"

    @field_validator("webtoactions_data_dir", "frontend_dist_dir", mode="after")
    @classmethod
    def anchor_data_dir_to_repo_root(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return REPO_ROOT / value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
