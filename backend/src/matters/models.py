from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models import Base


class Matter(Base):
    __tablename__ = "matter"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    
    case_number: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    division: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Drafting")
    
    verification_done: Mapped[int] = mapped_column(Integer, default=0)
    verification_total: Mapped[int] = mapped_column(Integer, default=0)
    last_activity: Mapped[str | None] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to user
    user = relationship("User", backref="matters")
