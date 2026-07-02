import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    # Every datetime column is timestamptz (spec 7: timestamptz everywhere).
    # Required for PostgreSQL+asyncpg: the app writes timezone-aware datetimes,
    # which asyncpg rejects on naive TIMESTAMP columns.
    type_annotation_map = {datetime: DateTime(timezone=True)}


class UUIDPKMixin:
    # Mapped[uuid.UUID] -> sa.Uuid: native UUID on PostgreSQL, CHAR(32) on SQLite.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
