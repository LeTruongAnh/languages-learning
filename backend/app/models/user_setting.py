import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class UserSetting(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Ho_Chi_Minh", nullable=False)
    auto_speak_on_card_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    speak_example: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    speech_rate: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.90"), nullable=False
    )
    speech_volume: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("1.00"), nullable=False
    )
    theme: Mapped[str] = mapped_column(String(30), default="system", nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_hour: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
