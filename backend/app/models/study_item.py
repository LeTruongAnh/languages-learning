"""Catalog item — CONTENT ONLY, shared by all users, managed by admins.
Per-user SRS state lives in user_item_progress (lazy rows)."""

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class StudyItem(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "study_items"
    __table_args__ = (
        CheckConstraint("item_type in ('VOCABULARY', 'SENTENCE')", name="ck_item_type"),
        Index("idx_study_items_language", "language_id"),
        Index("idx_study_items_type", "language_id", "item_type"),
        Index("idx_study_items_archived", "is_archived"),
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
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
