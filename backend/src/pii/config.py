from pydantic_settings import BaseSettings, SettingsConfigDict


class PiiConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PII_", env_file=".env", extra="ignore"
    )

    MODEL_NAME: str = "openai/privacy-filter"
    DEVICE: str = "cpu"
    CONFIDENCE_THRESHOLD: float = 0.5


pii_settings = PiiConfig()
