from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from src.models import CustomBaseModel


class IngestionRunCreate(CustomBaseModel):
    start_url: str = "https://new.kenyalaw.org/judgments/KEELC/"
    max_pages: int = Field(default=1, ge=1, le=25)
    max_documents: int = Field(default=25, ge=1, le=500)
    dry_run: bool = False


class IngestionRunRead(CustomBaseModel):
    id: int
    source: str
    scope: str
    status: str
    dry_run: bool
    started_at: datetime
    finished_at: datetime | None = None
    discovered_count: int
    fetched_count: int
    indexed_count: int
    skipped_count: int
    failed_count: int

    model_config = ConfigDict(from_attributes=True)


class IngestionEventRead(CustomBaseModel):
    id: int
    ingestion_run_id: int
    event_type: str
    stage: str
    message: str
    url: str | None = None
    error_type: str | None = None
    counts: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PineconePreflightStatus(CustomBaseModel):
    status: str
    message: str
    index_name: str | None = None
    embedding_model: str | None = None
    embedding_dimension: int | None = None
    index_dimension: int | None = None
    error_type: str | None = None


class CorpusStats(CustomBaseModel):
    source: str = "Kenya Law"
    scope: str = "elc"
    documents: int
    indexed_documents: int
    chunks: int
    failed_runs: int
    latest_run: IngestionRunRead | None = None
    preflight: PineconePreflightStatus | None = None


class CaseChunkRead(CustomBaseModel):
    id: int
    chunk_index: int
    text: str
    text_hash: str
    section_label: str | None = None
    pinecone_vector_id: str | None = None
    created_at: datetime


class CaseDocumentSummary(CustomBaseModel):
    id: int
    canonical_url: str
    title: str
    neutral_citation: str | None = None
    court: str | None = None
    judgment_date: str | None = None
    topic_tags: list[str] = []
    source_format: str
    source_document_url: str | None = None
    extraction_status: str = "valid"
    extraction_error: str | None = None
    extracted_at: datetime | None = None
    text_quality_score: int = 0
    fetch_status: str
    indexed_at: datetime | None = None
    stored_at: datetime | None = None
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime
    text_length: int
    chunk_count: int
    last_ingestion_run_id: int | None = None


class CaseDocumentList(CustomBaseModel):
    documents: list[CaseDocumentSummary]
    total: int
    page: int
    page_size: int


class CaseDocumentDetail(CaseDocumentSummary):
    normalized_text: str | None = None
    chunks: list[CaseChunkRead] = []
