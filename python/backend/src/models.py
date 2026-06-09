import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any

from experiment_tracker_shared import UtcNaiveDateTime, utc_now_naive

from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    Integer,
    Float,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from advanced_alchemy.base import UUIDBase as AdvancedUUIDBase
from sqlalchemy import Index, text


class Base(DeclarativeBase):
    pass


class DbMetadata(Base):
    """Single-row schema marker (``id`` is always ``1``)."""

    __tablename__ = "db_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False)


class UUIDBase(Base, AdvancedUUIDBase):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ExperimentStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class ExperimentDataType(str, Enum):
    """Supported generic experiment-data record types.

    Args:
        None. Enum members are fixed string values persisted in the database.

    Result:
        Type discriminator used by ``ExperimentData`` rows; currently supports
        snapshot metadata.
    """

    SNAPSHOT = "snapshot"
    HPARAMS = "hparams"


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    TESTING = "testing"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class MetricAggregation(str, Enum):
    LAST = "last"
    BEST = "best"
    AVERAGE = "average"


class MetricDirection(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class TeamMember(UUIDBase):
    __tablename__ = "team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[Role] = mapped_column(
        SQLEnum(Role), default=Role.MEMBER, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive, nullable=False
    )

    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="member_links",
        lazy="raise",
        overlaps="members,teams",
    )
    user: Mapped["User"] = relationship("User", lazy="raise", overlaps="teams,members")


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    display_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive
    )

    teams: Mapped[List["Team"]] = relationship(
        "Team",
        secondary="team_members",
        back_populates="members",
        lazy="raise",
    )
    owned_teams: Mapped[List["Team"]] = relationship(
        "Team", back_populates="owner", foreign_keys="Team.owner_id", lazy="raise"
    )
    api_tokens: Mapped[List["ApiToken"]] = relationship(
        "ApiToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class ApiToken(UUIDBase):
    __tablename__ = "api_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        UtcNaiveDateTime, nullable=True
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        UtcNaiveDateTime, nullable=True
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="api_tokens", lazy="raise"
    )


class Team(UUIDBase):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive
    )

    owner: Mapped["User"] = relationship(
        "User", back_populates="owned_teams", foreign_keys=[owner_id]
    )
    member_links: Mapped[List["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="team",
        lazy="raise",
        overlaps="members,teams",
        passive_deletes=True,
    )
    members: Mapped[List["User"]] = relationship(
        "User",
        secondary="team_members",
        back_populates="teams",
        lazy="raise",
        passive_deletes=True,
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="team",
        lazy="raise",
        passive_deletes=True,
    )


class Project(UUIDBase):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(String(512), default="")
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    settings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive
    )

    owner: Mapped["User"] = relationship("User", lazy="raise")
    team: Mapped[Optional["Team"]] = relationship(
        "Team", back_populates="projects", lazy="raise"
    )
    experiments: Mapped[List["Experiment"]] = relationship(
        "Experiment",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    hypotheses: Mapped[List["Hypothesis"]] = relationship(
        "Hypothesis",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    reports: Mapped[List["ProjectReport"]] = relationship(
        "ProjectReport",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class Experiment(UUIDBase):
    """Training run tracked inside a project.

    Args:
        project_id: Project that owns the experiment.
        name: Display name for the experiment.
        description: Optional longer description.
        status: Current lifecycle status.
        parent_experiment_id: Optional parent experiment for lineage.
        root_experiment_id: Optional root experiment for lineage trees.
        features: JSON feature hierarchy attached to the experiment.
        progress: Integer progress percentage.
        color: UI color used to distinguish the experiment.
        order: Project-local ordering value.
        tags: Optional list of experiment tags.
        started_by: Optional user UUID that started the experiment.
        created_at: Creation timestamp.
        started_at: Optional start timestamp.
        completed_at: Optional completion timestamp.
        project: SQLAlchemy relationship to the owning project.
        parent: SQLAlchemy relationship to the parent experiment.
        metrics: SQLAlchemy relationship to point-in-time metric rows.
        data_items: SQLAlchemy relationship to generic experiment-data rows.

    Result:
        SQLAlchemy model representing experiment metadata, lineage, UI state,
        metrics, and attached data records.
    """

    __tablename__ = "experiments"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[ExperimentStatus] = mapped_column(
        SQLEnum(ExperimentStatus), default=ExperimentStatus.PLANNED
    )
    parent_experiment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
    )
    root_experiment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    features: Mapped[List[dict[str, Any]]] = mapped_column(JSONB, default=list)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str] = mapped_column(String(20), default="#3b82f6")
    order: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[List[str] | None] = mapped_column(JSONB, default=list, nullable=True)
    started_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        UtcNaiveDateTime, nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        UtcNaiveDateTime, nullable=True
    )

    project: Mapped["Project"] = relationship(
        "Project", back_populates="experiments", lazy="raise"
    )
    parent: Mapped[Optional["Experiment"]] = relationship(
        "Experiment", remote_side="Experiment.id", lazy="raise"
    )
    metrics: Mapped[List["Metric"]] = relationship(
        "Metric",
        back_populates="experiment",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    data_items: Mapped[List["ExperimentData"]] = relationship(
        "ExperimentData",
        back_populates="experiment",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class ExperimentData(UUIDBase):
    """Generic metadata row attached to an experiment.

    Args:
        experiment_id: Experiment that owns the data row.
        type: Logical record type stored in this row.
        data: JSON payload for the type-specific metadata.
        created_at: Timestamp assigned when the row is inserted.
        updated_at: Timestamp updated when the row changes.
        experiment: SQLAlchemy relationship back to the owning experiment.

    Result:
        SQLAlchemy model backing experiment snapshot metadata and future
        experiment-scoped data types.
    """

    __tablename__ = "experiment_data"
    __table_args__ = (
        UniqueConstraint("experiment_id", "type", name="uq_experiment_data_experiment_type"),
        Index("ix_experiment_data_experiment_type", "experiment_id", "type"),
    )

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[ExperimentDataType] = mapped_column(
        SQLEnum(
            ExperimentDataType,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            name="experiment_data_type",
        ),
        nullable=False,
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
        nullable=False,
    )

    experiment: Mapped["Experiment"] = relationship(
        "Experiment", back_populates="data_items", lazy="raise"
    )


class Hypothesis(UUIDBase):
    __tablename__ = "hypotheses"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[HypothesisStatus] = mapped_column(
        SQLEnum(HypothesisStatus), default=HypothesisStatus.PROPOSED
    )
    target_metrics: Mapped[List[str]] = mapped_column(JSONB, default=list)
    baseline: Mapped[str] = mapped_column(String(512), default="root")
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive, onupdate=utc_now_naive
    )

    project: Mapped["Project"] = relationship(
        "Project", back_populates="hypotheses", lazy="raise"
    )


class ProjectReport(UUIDBase):
    """Rich-text experiment report (Tiptap JSON document) scoped to a project."""

    __tablename__ = "project_reports"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive, onupdate=utc_now_naive
    )

    project: Mapped["Project"] = relationship(
        "Project", back_populates="reports", lazy="raise"
    )


class Metric(UUIDBase):
    __tablename__ = "metrics"
    __table_args__ = (
        # Nullable `label` needs partial unique indexes: one row per (experiment, name) when
        # unlabeled, and one per (experiment, name, label) when labeled.
        Index(
            "uq_metrics_experiment_name_label",
            "experiment_id",
            "name",
            "label",
            unique=True,
            postgresql_where=text("label IS NOT NULL"),
            sqlite_where=text("label IS NOT NULL"),
        ),
        Index(
            "uq_metrics_experiment_name_unlabeled",
            "experiment_id",
            "name",
            unique=True,
            postgresql_where=text("label IS NULL"),
            sqlite_where=text("label IS NULL"),
        ),
    )

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcNaiveDateTime, default=utc_now_naive
    )

    experiment: Mapped["Experiment"] = relationship(
        "Experiment", back_populates="metrics", lazy="raise"
    )


class Permission(UUIDBase):
    """
    Отдельная запись для каждого права.
    Например: "Alex может создавать эксперименты в Team Alpha".
    """

    __tablename__ = "permissions"

    # Кто? (user_id)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Где? (team_id или project_id)
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # Какое право?
    action: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # "create_experiment", "delete_metric"

    # Включено/выключено?
    allowed: Mapped[bool] = mapped_column(Boolean, default=True)

    # Временные рамки (опционально)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        UtcNaiveDateTime, nullable=True
    )

    # Индексы для скорости
    __table_args__ = (
        Index("ix_permissions_user_team", user_id, team_id),
        Index("ix_permissions_user_action", user_id, action),
    )
