from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Legal Text Cleaner Configuration ──────────────────────────────
    SOURCES_DIR: str = "sources"
    OUTPUT_DIR: str = "cleaned"
    LOG_LEVEL: str = "INFO"

    # ── RAG Pipeline Configuration ────────────────────────────────────
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "legal-docs"

    # Chunking parameters
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 150

    # Environment
    ENVIRONMENT: str = "local"
    DATABASE_URL: str = "sqlite+aiosqlite:///./legal_docs.db"


settings = Settings()
