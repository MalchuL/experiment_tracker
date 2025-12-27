import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Table, Integer, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from fastapi_users.db import SQLAlchemyBaseUserTableUUID


class Base(DeclarativeBase):
    pass


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


class MetricDirection(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


team_members = Table(
    "team_members",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("team_id", UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", SQLEnum(TeamRole), default=TeamRole.MEMBER, nullable=False),
    Column("joined_at", DateTime, default=datetime.utcnow, nullable=False),
)


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"
    
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    teams: Mapped[List["Team"]] = relationship(
        "Team",
        secondary=team_members,
        back_populates="members",
        lazy="selectin"
    )
    owned_teams: Mapped[List["Team"]] = relationship(
        "Team",
        back_populates="owner",
        foreign_keys="Team.owner_id",
        lazy="selectin"
    )


class Team(Base):
    __tablename__ = "teams"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    owner: Mapped["User"] = relationship("User", back_populates="owned_teams", foreign_keys=[owner_id])
    members: Mapped[List["User"]] = relationship(
        "User",
        secondary=team_members,
        back_populates="teams",
        lazy="selectin"
    )
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="team", lazy="selectin")


class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSONB, default=list)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    owner: Mapped["User"] = relationship("User", lazy="selectin")
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="projects", lazy="selectin")
    experiments: Mapped[List["Experiment"]] = relationship("Experiment", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    hypotheses: Mapped[List["Hypothesis"]] = relationship("Hypothesis", back_populates="project", cascade="all, delete-orphan", lazy="selectin")


class Experiment(Base):
    __tablename__ = "experiments"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[ExperimentStatus] = mapped_column(SQLEnum(ExperimentStatus), default=ExperimentStatus.PLANNED)
    parent_experiment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("experiments.id", ondelete="SET NULL"), nullable=True)
    root_experiment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    features_diff: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    git_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str] = mapped_column(String(20), default="#3b82f6")
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    project: Mapped["Project"] = relationship("Project", back_populates="experiments", lazy="selectin")
    parent: Mapped[Optional["Experiment"]] = relationship("Experiment", remote_side="Experiment.id", lazy="selectin")
    metrics: Mapped[List["Metric"]] = relationship("Metric", back_populates="experiment", cascade="all, delete-orphan", lazy="selectin")


class Hypothesis(Base):
    __tablename__ = "hypotheses"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[HypothesisStatus] = mapped_column(SQLEnum(HypothesisStatus), default=HypothesisStatus.PROPOSED)
    target_metrics: Mapped[List[str]] = mapped_column(JSONB, default=list)
    baseline: Mapped[str] = mapped_column(String(100), default="root")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project: Mapped["Project"] = relationship("Project", back_populates="hypotheses", lazy="selectin")


class Metric(Base):
    __tablename__ = "metrics"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    step: Mapped[int] = mapped_column(Integer, default=0)
    direction: Mapped[MetricDirection] = mapped_column(SQLEnum(MetricDirection), default=MetricDirection.MINIMIZE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="metrics", lazy="selectin")
