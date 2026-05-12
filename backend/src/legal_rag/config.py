from pydantic_settings import BaseSettings, SettingsConfigDict


class LegalRAGConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    OPENAI_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "legal-docs"

    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 150


rag_settings = LegalRAGConfig()
