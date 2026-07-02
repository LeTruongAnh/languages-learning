import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class StudyItem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "study_items"
    __table_args__ = (
        CheckConstraint("item_type in ('VOCABULARY', 'SENTENCE')", name="ck_item_type"),
        Index("idx_study_items_user_language", "user_id", "language_id"),
        Index("idx_study_items_due", "user_id", "language_id", "next_review_date", "passed"),
        Index("idx_study_items_type", "user_id", "language_id", "item_type"),
        Index("idx_study_items_hard", "user_id", "hard_level"),
        Index("idx_study_items_archived", "user_id", "is_archived"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    language_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("languages.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    pronunciation: Mapped[str | None] = mapped_column(Text)
    vietnamese_meaning: Mapped[str | None] = mapped_column(Text)
    example: Mapped[str | None] = mapped_column(Text)
    example_vietnamese: Mapped[str | None] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(String(120))
    situation: Mapped[str | None] = mapped_column(String(120))
    difficulty: Mapped[str | None] = mapped_column(String(40))
    frequency_level: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(120))
    source_row: Mapped[int | None] = mapped_column(Integer)
    last_date_review: Mapped[date | None] = mapped_column(Date)
    next_review_date: Mapped[date | None] = mapped_column(Date)
    times_review: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_result: Mapped[str | None] = mapped_column(String(20))
    hard_level: Mapped[str] = mapped_column(String(30), default="Normal", nullable=False)
    # SM-2 (simplified): ease factor scales the next interval; interval_days
    # is the last applied interval so it can grow multiplicatively.
    ease: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.50"), nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
