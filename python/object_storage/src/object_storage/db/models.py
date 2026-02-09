"""SQLAlchemy models for the object storage service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import BigInteger, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as SAUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Experiment(Base):
    """Logical experiment grouping snapshots by name."""

    __tablename__ = "experiments"

    id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    snapshots: Mapped[list[Snapshot]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class Snapshot(Base):
    """Immutable snapshot of file manifest for a given experiment."""

    __tablename__ = "snapshots"

    id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    experiment_id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    manifest: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)

    experiment: Mapped[Experiment] = relationship(back_populates="snapshots")


class Blob(Base):
    """Content-addressed blob metadata (hash, size, ref_count)."""

    __tablename__ = "blobs"

    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ref_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
