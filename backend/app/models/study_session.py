import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class StudySession(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "study_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("languages.id", ondelete="SET NULL")
    )
    # LANGUAGE_DAILY | LANGUAGE_EXTRA | LANGUAGE_WEEKLY | HARD_ITEMS | ALL_DUE
    session_type: Mapped[str] = mapped_column(String(40), default="LANGUAGE_DAILY", nullable=False)
    # ACTIVE | COMPLETED | EXPIRED
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    study_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fail_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skip_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
