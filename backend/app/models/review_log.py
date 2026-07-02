import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPKMixin


class ReviewLog(Base, UUIDPKMixin):
    __tablename__ = "review_logs"
    __table_args__ = (
        CheckConstraint(
            "result in ('AGAIN', 'HARD', 'GOOD', 'EASY', 'SKIP', 'PASS', 'FAIL')",
            name="ck_review_result",
        ),
        Index("idx_review_logs_user_date", "user_id", "created_at"),
        Index("idx_review_logs_user_language_date", "user_id", "language_id", "created_at"),
        Index("idx_review_logs_item", "study_item_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    language_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("languages.id", ondelete="SET NULL")
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="SET NULL")
    )
    study_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("study_items.id", ondelete="SET NULL")
    )
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    old_times_review: Mapped[int | None] = mapped_column(Integer)
    new_times_review: Mapped[int | None] = mapped_column(Integer)
    old_passed: Mapped[bool | None] = mapped_column()
    new_passed: Mapped[bool | None] = mapped_column()
    old_wrong_count: Mapped[int | None] = mapped_column(Integer)
    new_wrong_count: Mapped[int | None] = mapped_column(Integer)
    old_hard_level: Mapped[str | None] = mapped_column(String(30))
    new_hard_level: Mapped[str | None] = mapped_column(String(30))
    old_next_review_date: Mapped[date | None] = mapped_column(Date)
    new_next_review_date: Mapped[date | None] = mapped_column(Date)
    # Extra old/new state so the review can be fully undone (Anki-style).
    old_ease: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    new_ease: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    old_interval_days: Mapped[int | None] = mapped_column(Integer)
    new_interval_days: Mapped[int | None] = mapped_column(Integer)
    old_last_result: Mapped[str | None] = mapped_column(String(20))
    old_last_date_review: Mapped[date | None] = mapped_column(Date)
    self_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    # Study date in the user's timezone - used by dashboard/streak queries.
    study_date: Mapped[date | None] = mapped_column(Date, index=True)
