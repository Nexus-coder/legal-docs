from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base


class DraftingRun(Base):
    __tablename__ = "drafting_run"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matter.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="running", index=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(150))
    subcategory: Mapped[str | None] = mapped_column(String(150))
    pleading_type: Mapped[str | None] = mapped_column(String(180))
    selected_document_types: Mapped[list[str] | None] = mapped_column(JSON)
    error_status: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    matter = relationship("Matter")
    events = relationship(
        "DraftingEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="DraftingEvent.id",
    )


class DraftingEvent(Base):
    __tablename__ = "drafting_event"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    drafting_run_id: Mapped[int] = mapped_column(
        ForeignKey("drafting_run.id"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    stage: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(80))
    error_type: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    run = relationship("DraftingRun", back_populates="events")
