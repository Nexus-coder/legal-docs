from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class LegalCleanerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    SOURCES_DIR: Path = Path("data/sources")
    OUTPUT_DIR: Path = Path("data/cleaned")
    LOG_LEVEL: str = "INFO"


cleaner_settings = LegalCleanerConfig()
