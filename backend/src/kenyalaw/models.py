from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base


class LegalSource(Base):
    __tablename__ = "legal_source"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    license: Mapped[str | None] = mapped_column(String(255))
    terms_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    documents = relationship("CaseDocument", back_populates="source")


class CaseDocument(Base):
    __tablename__ = "case_document"
    __table_args__ = (
        UniqueConstraint("canonical_url", name="case_document_canonical_url_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("legal_source.id"), index=True, nullable=False
    )
    canonical_url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    neutral_citation: Mapped[str | None] = mapped_column(String(255), index=True)
    court: Mapped[str | None] = mapped_column(String(180), index=True)
    judgment_date: Mapped[str | None] = mapped_column(String(40), index=True)
    topic_tags: Mapped[str | None] = mapped_column(Text)
    source_format: Mapped[str] = mapped_column(String(30), default="html")
    raw_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    normalized_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    fetch_status: Mapped[str] = mapped_column(String(40), default="discovered", index=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    source = relationship("LegalSource", back_populates="documents")
    chunks = relationship(
        "CaseChunk", back_populates="document", cascade="all, delete-orphan"
    )


class CaseChunk(Base):
    __tablename__ = "case_chunk"
    __table_args__ = (
        UniqueConstraint(
            "case_document_id", "chunk_index", name="case_chunk_document_index_key"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_document_id: Mapped[int] = mapped_column(
        ForeignKey("case_document.id"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    section_label: Mapped[str | None] = mapped_column(String(120))
    pinecone_vector_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    document = relationship("CaseDocument", back_populates="chunks")


class IngestionRun(Base):
    __tablename__ = "ingestion_run"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(120), default="Kenya Law")
    scope: Mapped[str] = mapped_column(String(80), default="elc")
    status: Mapped[str] = mapped_column(String(40), default="running", index=True)
    dry_run: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    indexed_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)

    errors = relationship(
        "IngestionError", back_populates="run", cascade="all, delete-orphan"
    )
    events = relationship(
        "IngestionEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="IngestionEvent.id",
    )


class IngestionError(Base):
    __tablename__ = "ingestion_error"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_run.id"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    error_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    run = relationship("IngestionRun", back_populates="errors")


class IngestionEvent(Base):
    __tablename__ = "ingestion_event"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_run.id"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    stage: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    error_type: Mapped[str | None] = mapped_column(String(80))
    counts: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    run = relationship("IngestionRun", back_populates="events")
