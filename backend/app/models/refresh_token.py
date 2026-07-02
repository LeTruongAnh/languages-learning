"""Refresh tokens with rotation support (not in original spec - see PLAN.md 1.2).

- token_hash: SHA-256 of the raw token; raw token is never stored.
- family_id: all tokens in one login chain share a family. If a revoked/rotated
  token is presented again (reuse attack), revoke the entire family.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class RefreshToken(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(default=None)
