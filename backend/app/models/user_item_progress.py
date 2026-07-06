"""Per-user SRS progress for a shared catalog item.

Created LAZILY: a user who never graded a card has NO row for it — the study
engine treats missing progress as a NEW card (LEFT JOIN). This keeps the DB
small and gives new accounts the full catalog instantly.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class UserItemProgress(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "user_item_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id"),
        Index("idx_progress_due", "user_id", "next_review_date", "passed"),
        Index("idx_progress_hard", "user_id", "hard_level"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("study_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    times_review: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_result: Mapped[str | None] = mapped_column(String(20))
    last_date_review: Mapped[date | None] = mapped_column(Date)
    next_review_date: Mapped[date | None] = mapped_column(Date)
    ease: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.50"), nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hard_level: Mapped[str] = mapped_column(String(30), default="Normal", nullable=False)
