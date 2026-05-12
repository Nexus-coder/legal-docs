from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTH_", env_file=".env", extra="ignore"
    )

    JWT_SECRET: str = "super-secret-dev-key"  # Should be overridden in .env
    JWT_ALG: str = "HS256"
    JWT_EXP_MINUTES: int = 60 * 24  # 24 hours
    
    # Password hashing rounds
    PWD_ROUNDS: int = 12


auth_settings = AuthConfig()
