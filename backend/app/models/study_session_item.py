import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPKMixin


class StudySessionItem(Base, UUIDPKMixin):
    __tablename__ = "study_session_items"
    __table_args__ = (UniqueConstraint("session_id", "study_item_id"),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    study_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("study_items.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # VOCAB_REVIEW | VOCAB_NEW | SENTENCE_REVIEW | SENTENCE_NEW
    planned_bucket: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str | None] = mapped_column(String(20))
    # Idempotency guard: if applied_at is set, review was already applied -
    # return existing state, never re-apply (spec 12.4).
    applied_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
