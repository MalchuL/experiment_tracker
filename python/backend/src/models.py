import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Any


def utc_now() -> datetime:
    """
    Get current UTC datetime as a naive datetime object.
    This replaces datetime.utcnow() which is deprecated.
    Returns a timezone-naive datetime representing UTC time.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Integer,
    Float,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from advanced_alchemy.base import UUIDBase as AdvancedUUIDBase
from sqlalchemy import Index


class Base(DeclarativeBase):
    pass


class UUIDBase(Base, AdvancedUUIDBase):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TeamRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ExperimentStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


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
    role: Mapped[TeamRole] = mapped_column(
        SQLEnum(TeamRole), default=TeamRole.MEMBER, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
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

    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    teams: Mapped[List["Team"]] = relationship(
        "Team",
        secondary="team_members",
        back_populates="members",
        lazy="raise",
    )
    owned_teams: Mapped[List["Team"]] = relationship(
        "Team", back_populates="owner", foreign_keys="Team.owner_id", lazy="raise"
    )


class Team(UUIDBase):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    owner: Mapped["User"] = relationship(
        "User", back_populates="owned_teams", foreign_keys=[owner_id]
    )
    member_links: Mapped[List["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="team",
        lazy="raise",
        overlaps="members,teams",
    )
    members: Mapped[List["User"]] = relationship(
        "User",
        secondary="team_members",
        back_populates="teams",
        lazy="raise",
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="team", lazy="raise"
    )


class Project(UUIDBase):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    metrics: Mapped[dict] = mapped_column(JSONB, default=list)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

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


class Experiment(UUIDBase):
    __tablename__ = "experiments"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
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
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    features_diff: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    git_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str] = mapped_column(String(20), default="#3b82f6")
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

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


class Hypothesis(UUIDBase):
    __tablename__ = "hypotheses"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[HypothesisStatus] = mapped_column(
        SQLEnum(HypothesisStatus), default=HypothesisStatus.PROPOSED
    )
    target_metrics: Mapped[List[str]] = mapped_column(JSONB, default=list)
    baseline: Mapped[str] = mapped_column(String(100), default="root")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    project: Mapped["Project"] = relationship(
        "Project", back_populates="hypotheses", lazy="raise"
    )


class Metric(UUIDBase):
    __tablename__ = "metrics"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    step: Mapped[int] = mapped_column(Integer, default=0)
    direction: Mapped[MetricDirection] = mapped_column(
        SQLEnum(MetricDirection), default=MetricDirection.MINIMIZE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

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
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Индексы для скорости
    __table_args__ = (
        Index("ix_permissions_user_team", user_id, team_id),
        Index("ix_permissions_user_action", user_id, action),
    )
