from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Language(Base, UUIDPKMixin, TimestampMixin):
    """Global catalog language (zh, en, ...) — admin-managed, shared by all."""

    __tablename__ = "languages"
    __table_args__ = (UniqueConstraint("code"),)

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    native_name: Mapped[str | None] = mapped_column(String(120))
    tts_lang: Mapped[str] = mapped_column(String(20), nullable=False)
    accent_color: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
