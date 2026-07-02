import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.types import IntList, StrList


class LanguageSetting(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "language_settings"
    __table_args__ = (UniqueConstraint("user_id", "language_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("languages.id", ondelete="CASCADE"), nullable=False
    )
    daily_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    vocabulary_ratio: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("0.700"), nullable=False
    )
    sentence_ratio: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("0.300"), nullable=False
    )
    new_ratio: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("0.600"), nullable=False
    )
    review_ratio: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), default=Decimal("0.400"), nullable=False
    )
    times_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    sentence_times_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    review_intervals: Mapped[list[int]] = mapped_column(
        IntList, default=lambda: [1, 3, 7], nullable=False
    )
    sentence_review_intervals: Mapped[list[int]] = mapped_column(
        IntList, default=lambda: [1, 3, 7], nullable=False
    )
    difficulty_filter: Mapped[list[str]] = mapped_column(
        StrList, default=lambda: ["ALL"], nullable=False
    )
    sentence_difficulty_filter: Mapped[list[str]] = mapped_column(
        StrList, default=lambda: ["ALL"], nullable=False
    )
    topic_filter: Mapped[list[str]] = mapped_column(
        StrList, default=lambda: ["ALL"], nullable=False
    )
    situation_filter: Mapped[list[str]] = mapped_column(
        StrList, default=lambda: ["ALL"], nullable=False
    )
    frequency_filter: Mapped[list[str]] = mapped_column(
        StrList, default=lambda: ["ALL"], nullable=False
    )
    include_passed_items: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    passed_review_after_days: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    reset_on_fail: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    avoid_same_day_repeat: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_mode: Mapped[str] = mapped_column(String(30), default="random", nullable=False)
    item_ordering: Mapped[str] = mapped_column(
        String(50), default="VOCAB_FIRST_WITH_REVIEW_PRIORITY", nullable=False
    )
    # Weekly review: day of week (MONDAY..SUNDAY) + max items
    weekly_review_day: Mapped[str] = mapped_column(String(10), default="SUNDAY", nullable=False)
    weekly_review_limit: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    # FRONT (word->meaning) | REVERSE (meaning->word) | LISTENING (audio->word) | MIXED
    study_direction: Mapped[str] = mapped_column(String(20), default="FRONT", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
