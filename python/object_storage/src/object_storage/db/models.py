"""SQLAlchemy models for the object storage service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import BigInteger, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as SAUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Snapshot(Base):
    """Immutable snapshot of file manifest for a given experiment."""

    __tablename__ = "snapshots"

    id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    manifest: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)


class TrackedBlob(Base):
    """
    Tracked blob metadata (hash, size, ref_count).
    Used to track blobs that are part of a snapshot to avoid duplicate uploads.
    """

    __tablename__ = "tracked_blobs"
    # We use the hash as the primary key because it is the content-addressable identifier for the blob.
    # The project_id is also a primary key because it is the identifier for the project that the blob belongs to.
    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), nullable=False, primary_key=True
    )
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ref_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
