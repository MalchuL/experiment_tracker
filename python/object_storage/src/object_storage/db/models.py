"""SQLAlchemy models for the object storage service."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID as PyUUID, uuid4

from experiment_tracker_shared import UtcNaiveDateTime
from sqlalchemy import BigInteger, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as SAUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Snapshot(Base):
    """Immutable snapshot of file manifest for a given experiment."""

    __tablename__ = "snapshots"

    id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    project_id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime,
        server_default=text("timezone('utc', now())"),
        nullable=False,
    )
    manifest: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)


class ProjectBlob(Base):
    """
    Tracked blob metadata (hash, size, ref_count).
    Used to track blobs that are part of a snapshot to avoid duplicate uploads.
    Don't have file name because different experiments can have different file names for the same blob.
    """

    __tablename__ = "tracked_blobs"
    # We use the hash as the primary key because it is the content-addressable identifier for the blob.
    # The project_id is also a primary key because it is the identifier for the project that the blob belongs to.
    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), nullable=False, primary_key=True
    )
    mime_type: Mapped[str] = mapped_column(
        String(255), nullable=False, default="application/octet-stream"
    )
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ref_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime,
        server_default=text("timezone('utc', now())"),
        nullable=False,
    )


class ExperimentBlob(Base):
    """
    Tracked blob metadata (hash, size, filename).
    Used to track blobs that are part experiment like config, weights, etc.
    """

    __tablename__ = "experiment_blobs"
    # We use the hash as the primary key because it is the content-addressable identifier for the blob.
    # The project_id is also a primary key because it is the identifier for the project that the blob belongs to.
    id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    artifact_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=lambda: {},
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime,
        server_default=text("timezone('utc', now())"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime,
        server_default=text("timezone('utc', now())"),
        nullable=False,
        onupdate=text("timezone('utc', now())"),
    )


class Bucket(Base):
    """
    Bucket metadata (name, path).
    Used to track buckets that are used to store blobs.
    Project-scoped CAS uses ``experiment_id IS NULL``; per-experiment buckets set ``experiment_id``.
    """

    __tablename__ = "buckets"
    __table_args__ = (
        Index(
            "uq_buckets_project_scope",
            "project_id",
            unique=True,
            postgresql_where=text("experiment_id IS NULL"),
        ),
        Index(
            "uq_buckets_project_experiment",
            "project_id",
            "experiment_id",
            unique=True,
            postgresql_where=text("experiment_id IS NOT NULL"),
        ),
    )
    id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    project_id: Mapped[PyUUID] = mapped_column(
        SAUUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[PyUUID | None] = mapped_column(
        SAUUID(as_uuid=True), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime,
        server_default=text("timezone('utc', now())"),
        nullable=False,
    )
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
