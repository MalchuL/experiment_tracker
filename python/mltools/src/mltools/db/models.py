"""Relational persistence models for importance jobs and their outputs."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp.

    Returns:
        datetime: Current UTC time for persistence defaults.
    """
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all MLTools relational persistence models."""

    pass


class JobStatus(str, enum.Enum):
    """Persisted lifecycle states for asynchronous analysis jobs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UUIDMixin:
    """Provide a generated UUID primary key to persistence models."""
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class HparamImportanceJob(UUIDMixin, Base):
    """Root persistence entity for one hyperparameter-importance analysis job.

    Result:
        Job row containing lifecycle state, immutable request configuration, target
        metrics, timestamps, and relationships to all analysis outputs.
    """
    __tablename__ = "hparam_importance_jobs"
    __table_args__ = (Index("ix_hparam_jobs_project_created", "project_id", "created_at"),)

    project_id: Mapped[uuid.UUID] = mapped_column(index=True)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING.value)
    stage: Mapped[str] = mapped_column(String(64), default="created")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    target_metrics: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    config: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    experiments: Mapped[list[HparamImportanceJobExperiment]] = relationship(cascade="all, delete-orphan")
    metric_experiments: Mapped[list[HparamImportanceJobMetricExperiment]] = relationship(cascade="all, delete-orphan")
    parameters: Mapped[list[HparamImportanceJobParameter]] = relationship(cascade="all, delete-orphan")
    results: Mapped[list[HparamImportanceResult]] = relationship(cascade="all, delete-orphan")
    model_artifacts: Mapped[list[HparamImportanceModelArtifact]] = relationship(cascade="all, delete-orphan")
    messages: Mapped[list[HparamImportanceJobMessage]] = relationship(cascade="all, delete-orphan")


class HparamImportanceJobExperiment(UUIDMixin, Base):
    """Record whether one project experiment participated in a job."""
    __tablename__ = "hparam_importance_job_experiments"
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hparam_importance_jobs.id", ondelete="CASCADE"), index=True)
    experiment_id: Mapped[uuid.UUID] = mapped_column(index=True)
    experiment_name: Mapped[str] = mapped_column(String(512))
    included: Mapped[bool] = mapped_column(Boolean)
    exclude_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_hparams: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class HparamImportanceJobMetricExperiment(UUIDMixin, Base):
    """Record per-target-metric usage and target value for one experiment."""
    __tablename__ = "hparam_importance_job_metric_experiments"
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hparam_importance_jobs.id", ondelete="CASCADE"), index=True)
    target_metric: Mapped[dict[str, Any]] = mapped_column(JSON)
    experiment_id: Mapped[uuid.UUID] = mapped_column(index=True)
    used: Mapped[bool] = mapped_column(Boolean)
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_value_strategy: Mapped[str | None] = mapped_column(String(32), nullable=True)


class HparamImportanceJobParameter(UUIDMixin, Base):
    """Persist inferred and selected processing metadata for one flattened hparam."""
    __tablename__ = "hparam_importance_job_parameters"
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hparam_importance_jobs.id", ondelete="CASCADE"), index=True)
    flat_key: Mapped[str] = mapped_column(String(2048))
    path: Mapped[list[str]] = mapped_column(JSON)
    inferred_type: Mapped[str] = mapped_column(String(32))
    selected_type: Mapped[str] = mapped_column(String(32))
    processing_strategy: Mapped[str] = mapped_column(String(32))
    array_strategy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    included: Mapped[bool] = mapped_column(Boolean)
    exclude_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class HparamImportanceResult(UUIDMixin, Base):
    """Persist one ranked hparam importance result for a target metric."""
    __tablename__ = "hparam_importance_results"
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hparam_importance_jobs.id", ondelete="CASCADE"), index=True)
    target_metric: Mapped[dict[str, Any]] = mapped_column(JSON)
    flat_key: Mapped[str] = mapped_column(String(2048))
    path: Mapped[list[str]] = mapped_column(JSON)
    importance: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    importance_method: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class HparamImportanceModelArtifact(UUIDMixin, Base):
    """Persist metadata and the object-storage reference for a trained model."""
    __tablename__ = "hparam_importance_model_artifacts"
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hparam_importance_jobs.id", ondelete="CASCADE"), index=True)
    target_metric: Mapped[dict[str, Any]] = mapped_column(JSON)
    model_type: Mapped[str] = mapped_column(String(128))
    object_storage_bucket: Mapped[str] = mapped_column(String(255))
    object_storage_key: Mapped[str] = mapped_column(String(2048))
    artifact_format: Mapped[str] = mapped_column(String(32))
    train_rows: Mapped[int] = mapped_column(Integer)
    validation_rows: Mapped[int] = mapped_column(Integer)
    feature_count: Mapped[int] = mapped_column(Integer)
    score_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class HparamImportanceJobMessage(UUIDMixin, Base):
    """Persist an informational, warning, or error message emitted by a job."""
    __tablename__ = "hparam_importance_job_messages"
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hparam_importance_jobs.id", ondelete="CASCADE"), index=True)
    level: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    flat_key: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    target_metric: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
"""SQLAlchemy persistence models for hyperparameter-importance job history.

The MLTools database stores analysis metadata, participation records, results,
messages, and object-storage references. Raw experiment hyperparameters remain in
the main backend database.
"""
