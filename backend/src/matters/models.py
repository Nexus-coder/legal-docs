from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models import Base


class Matter(Base):
    __tablename__ = "matter"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    
    case_number: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    division: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Drafting")
    workflow_state: Mapped[str] = mapped_column(String(50), default="created", index=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(150))
    subcategory: Mapped[str | None] = mapped_column(String(150))
    raw_facts: Mapped[str | None] = mapped_column(Text)
    masked_facts: Mapped[str | None] = mapped_column(Text)
    pii_entity_count: Mapped[int] = mapped_column(Integer, default=0)
    draft_content: Mapped[str | None] = mapped_column(Text)
    drafting_error: Mapped[str | None] = mapped_column(String(80))
    masked_at: Mapped[datetime | None] = mapped_column(DateTime)
    drafted_at: Mapped[datetime | None] = mapped_column(DateTime)
    citations_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    export_ready_at: Mapped[datetime | None] = mapped_column(DateTime)
    
    verification_done: Mapped[int] = mapped_column(Integer, default=0)
    verification_total: Mapped[int] = mapped_column(Integer, default=0)
    last_activity: Mapped[str | None] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to user
    user = relationship("User", backref="matters")
    activities = relationship(
        "MatterActivity", back_populates="matter", cascade="all, delete-orphan"
    )
    citation_evidence = relationship(
        "CitationEvidence", back_populates="matter", cascade="all, delete-orphan"
    )
    draft_documents = relationship(
        "DraftDocument", back_populates="matter", cascade="all, delete-orphan"
    )


class MatterActivity(Base):
    __tablename__ = "matter_activity"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matter.id"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    matter = relationship("Matter", back_populates="activities")


class CitationEvidence(Base):
    __tablename__ = "citation_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matter.id"), index=True, nullable=False)
    citation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    matter = relationship("Matter", back_populates="citation_evidence")


class DraftDocument(Base):
    __tablename__ = "draft_document"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matter.id"), index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    error_status: Mapped[str | None] = mapped_column(String(80))
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    matter = relationship("Matter", back_populates="draft_documents")
