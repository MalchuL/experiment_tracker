"""
Pytest configuration and fixtures for testing.
"""

import os
import sys
from types import MethodType
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID

from models import Base, User, Team, TeamMember
from domain.api_tokens.repository import ApiTokenRepository
from domain.api_tokens.service import ApiTokenService
from domain.experiments.repository import ExperimentRepository
from domain.experiments.service import ExperimentService
from domain.hypotheses.repository import HypothesisRepository
from domain.hypotheses.service import HypothesisService
from domain.metrics.repository import MetricRepository
from domain.metrics.service import MetricService
from domain.projects.dashboard.service import DashboardService
from domain.projects.repository import ProjectRepository
from domain.projects.service import ProjectService
from domain.rbac.repository import PermissionRepository
from domain.rbac.service import PermissionService
from domain.rbac.wrapper import PermissionChecker
from domain.team.teams.repository import TeamRepository
from domain.team.teams.service import TeamService
from db.utils import build_async_database_url

# Use in-memory SQLite database for tests by default
DEFAULT_DATABASE_UR = "sqlite+aiosqlite:///:memory:"
TEST_DATABASE_URL = os.getenv("DATABASE_UR", DEFAULT_DATABASE_UR) or DEFAULT_DATABASE_UR


def _patch_session_commit_to_flush(session: AsyncSession) -> None:
    """Keep test data in transaction by converting commit to flush."""

    async def _commit_as_flush(self: AsyncSession) -> None:
        await self.flush()

    session.commit = MethodType(_commit_as_flush, session)


# Replace JSONB columns with JSON for SQLite compatibility
# This must be done before any models are instantiated
def _patch_jsonb_columns():
    """Replace JSONB columns with JSON for SQLite compatibility."""
    if TEST_DATABASE_URL.startswith("sqlite"):
        # Import all models to ensure they're in metadata
        from models import Project, Experiment, Hypothesis, Metric  # noqa: F401

        # Wait for all relationships to be configured
        import sqlalchemy.orm

        for mapper in Base.registry.mappers:
            mapper._check_configure()

        # Now patch JSONB columns for SQLite compatibility
        # Note: We keep UUID columns as-is and use adapters to convert them
        for table in Base.metadata.tables.values():
            for column in table.columns:
                # Check if the column type is JSONB
                if (
                    isinstance(column.type, JSONB)
                    or type(column.type).__name__ == "JSONB"
                ):
                    column.type = JSON()
                # For UUID columns, we'll use adapters instead of changing the type
                # This allows SQLAlchemy to handle UUIDs correctly


@pytest.fixture(scope="function")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create a test database engine for each test.

    Function-scoped to avoid event loop issues with asyncpg.
    Uses in-memory SQLite by default for fast tests.
    Set TEST_DATABASE_URL environment variable to use a different database.
    """
    # For SQLite in-memory, use StaticPool to allow multiple connections
    if TEST_DATABASE_URL.startswith("sqlite"):
        import uuid
        import aiosqlite

        # Register UUID adapter for SQLite to convert UUID -> str on write
        def adapt_uuid(uuid_obj):
            return str(uuid_obj)

        # Register converter for SQLite to convert str -> UUID on read
        def convert_uuid(s):
            return uuid.UUID(s.decode() if isinstance(s, bytes) else s)

        # Register adapters for aiosqlite
        aiosqlite.register_adapter(uuid.UUID, adapt_uuid)
        aiosqlite.register_converter("UUID", convert_uuid)

        # Also need to patch the UUID type to work with SQLite
        # Create a custom UUID type that uses String for SQLite and UUID for PostgreSQL
        from sqlalchemy.types import TypeDecorator
        import uuid

        class SQLiteUUID(TypeDecorator):
            """UUID type that uses String for SQLite and UUID for PostgreSQL."""

            impl = String(36)
            cache_ok = True

            def load_dialect_impl(self, dialect):
                if dialect.name == "sqlite":
                    return dialect.type_descriptor(String(36))
                else:
                    return dialect.type_descriptor(PostgresUUID(as_uuid=True))

            def process_bind_param(self, value, dialect):
                if value is None:
                    return value
                if isinstance(value, uuid.UUID):
                    return str(value)
                return value

            def process_result_value(self, value, dialect):
                if value is None:
                    return value
                if isinstance(value, str):
                    return uuid.UUID(value)
                return value

        # Replace UUID columns with SQLiteUUID
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, PostgresUUID) or (
                    hasattr(column.type, "__class__")
                    and "UUID" in column.type.__class__.__name__
                    and "postgresql" in str(type(column.type))
                ):
                    column.type = SQLiteUUID()

        engine = create_async_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:
        # For PostgreSQL, configure engine to avoid connection pool issues
        engine = create_async_engine(
            build_async_database_url(TEST_DATABASE_URL),
            echo=False,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,  # Limit pool size for tests
            max_overflow=0,  # Don't allow overflow connections
        )

    # Create all tables
    # Note: For SQLite, JSONB columns will cause errors.
    # Use PostgreSQL for testing or set TEST_DATABASE_URL to a PostgreSQL database.
    async with engine.begin() as conn:
        # For SQLite, we need to handle JSONB -> JSON and UUID -> String conversion
        if TEST_DATABASE_URL.startswith("sqlite"):
            import uuid
            from sqlalchemy import event as sqlalchemy_event

            # Convert UUID objects to strings for SQLite
            @sqlalchemy_event.listens_for(engine.sync_engine, "before_cursor_execute")
            def receive_before_cursor_execute(
                conn, cursor, statement, parameters, context, executemany
            ):
                # Replace JSONB with JSON in SQL statements for SQLite
                if isinstance(statement, str):
                    statement = statement.replace("JSONB", "JSON")

                # Convert UUID parameters to strings
                if parameters:
                    if isinstance(parameters, dict):
                        new_params = {}
                        for key, value in parameters.items():
                            if isinstance(value, uuid.UUID):
                                new_params[key] = str(value)
                            else:
                                new_params[key] = value
                        parameters = new_params
                    elif isinstance(parameters, (list, tuple)):
                        new_params = []
                        for value in parameters:
                            if isinstance(value, uuid.UUID):
                                new_params.append(str(value))
                            else:
                                new_params.append(value)
                        parameters = (
                            tuple(new_params)
                            if isinstance(parameters, tuple)
                            else new_params
                        )

                return statement, parameters

            # Patch the metadata before creation
            _patch_jsonb_columns()

        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for each test.

    Automatically rolls back all changes after each test.
    Uses savepoints (nested transactions) for PostgreSQL and connection-level
    transactions for SQLite.
    """
    async_session_maker = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    # Use different transaction strategies for SQLite vs PostgreSQL
    if TEST_DATABASE_URL.startswith("sqlite"):
        # For SQLite, use connection-level transaction
        async with test_engine.connect() as connection:
            # Start a transaction on the connection
            transaction = await connection.begin()
            # Bind the session to this connection
            async with async_session_maker(bind=connection) as session:
                _patch_session_commit_to_flush(session)
                try:
                    yield session
                finally:
                    # Rollback the transaction to clean up
                    await transaction.rollback()
    else:
        # For PostgreSQL and other databases, use a simple session with manual rollback
        # This avoids the asyncpg "another operation is in progress" error
        # by not binding to a connection and letting SQLAlchemy manage the connection pool
        async with async_session_maker() as session:
            _patch_session_commit_to_flush(session)
            # Start a transaction manually (don't use begin() context manager as it commits)
            # Type ignore because AsyncSessionTransaction is compatible for our use case
            transaction = await session.begin()  # type: ignore[assignment]
            try:
                yield session
            finally:
                # Always rollback to clean up test data
                # This ensures test isolation
                try:
                    await transaction.rollback()
                except Exception:
                    pass


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=None,  # Let SQLAlchemy generate UUID
        email="test@example.com",
        hashed_password="hashed_password_123",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_2(db_session: AsyncSession) -> User:
    """Create a second test user."""
    user = User(
        id=None,
        email="test2@example.com",
        hashed_password="hashed_password_456",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_team(db_session: AsyncSession, test_user: User) -> Team:
    """Create a test team owned by test_user."""
    team = Team(
        id=None,
        name="Test Team",
        description="A test team",
        owner_id=test_user.id,
    )
    db_session.add(team)
    await db_session.flush()
    await db_session.refresh(team)
    return team


@pytest.fixture
async def team_repository(db_session: AsyncSession) -> TeamRepository:
    """Create a TeamRepository instance."""
    return TeamRepository(db_session)


@pytest.fixture(autouse=True)
def service_constructor_compat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Backwards-compatible service constructors for legacy tests."""

    original_permission_init = PermissionService.__init__
    original_api_token_init = ApiTokenService.__init__
    original_experiment_init = ExperimentService.__init__
    original_hypothesis_init = HypothesisService.__init__
    original_metric_init = MetricService.__init__
    original_team_init = TeamService.__init__
    original_project_init = ProjectService.__init__
    original_dashboard_init = DashboardService.__init__
    original_permission_checker_init = PermissionChecker.__init__

    def _permission_init_compat(
        self,
        db: AsyncSession,
        permission_repository: PermissionRepository | None = None,
        project_repository: ProjectRepository | None = None,
        auto_commit: bool = False,
    ) -> None:
        permission_repository = permission_repository or PermissionRepository(db)
        project_repository = project_repository or ProjectRepository(db)
        original_permission_init(
            self,
            db,
            permission_repository=permission_repository,
            project_repository=project_repository,
            auto_commit=auto_commit,
        )

    def _api_token_init_compat(
        self,
        db: AsyncSession,
        api_token_repository: ApiTokenRepository | None = None,
    ) -> None:
        api_token_repository = api_token_repository or ApiTokenRepository(db)
        original_api_token_init(self, db, api_token_repository=api_token_repository)

    def _make_permission_checker(
        db: AsyncSession, user: User | None = None
    ) -> PermissionChecker:
        from domain.rbac.deps import build_permission_checker

        permission_service = PermissionService(
            db,
            permission_repository=PermissionRepository(db),
            project_repository=ProjectRepository(db),
            auto_commit=False,
        )
        if user is not None:
            return build_permission_checker(user, db, permission_service)
        return PermissionChecker(db, permission_service)

    def _permission_checker_init_compat(
        self,
        db: AsyncSession,
        permission_service: PermissionService | None = None,
    ) -> None:
        permission_service = permission_service or PermissionService(
            db,
            permission_repository=PermissionRepository(db),
            project_repository=ProjectRepository(db),
            auto_commit=False,
        )
        original_permission_checker_init(self, db, permission_service)

    def _experiment_init_compat(
        self,
        db: AsyncSession,
        experiment_repository: ExperimentRepository | None = None,
        permission_checker: PermissionChecker | None = None,
        scalars_service=None,
        object_storage_client=None,
    ) -> None:
        experiment_repository = experiment_repository or ExperimentRepository(db)
        permission_checker = permission_checker or _make_permission_checker(db)
        original_experiment_init(
            self,
            db,
            experiment_repository=experiment_repository,
            permission_checker=permission_checker,
            scalars_service=scalars_service,
            object_storage_client=object_storage_client,
        )

    def _hypothesis_init_compat(
        self,
        db: AsyncSession,
        hypothesis_repository: HypothesisRepository | None = None,
        permission_checker: PermissionChecker | None = None,
    ) -> None:
        hypothesis_repository = hypothesis_repository or HypothesisRepository(db)
        permission_checker = permission_checker or _make_permission_checker(db)
        original_hypothesis_init(
            self,
            db,
            hypothesis_repository=hypothesis_repository,
            permission_checker=permission_checker,
        )

    def _metric_init_compat(
        self,
        db: AsyncSession,
        metric_repository: MetricRepository | None = None,
        experiment_repository: ExperimentRepository | None = None,
        permission_checker: PermissionChecker | None = None,
    ) -> None:
        metric_repository = metric_repository or MetricRepository(db)
        experiment_repository = experiment_repository or ExperimentRepository(db)
        permission_checker = permission_checker or _make_permission_checker(db)
        original_metric_init(
            self,
            db,
            metric_repository=metric_repository,
            experiment_repository=experiment_repository,
            permission_checker=permission_checker,
        )

    def _team_init_compat(
        self,
        db: AsyncSession,
        team_repository: TeamRepository | None = None,
        permission_checker: PermissionChecker | None = None,
        permission_service: PermissionService | None = None,
        auto_commit: bool | None = None,
    ) -> None:
        del auto_commit
        team_repository = team_repository or TeamRepository(db)
        permission_checker = permission_checker or _make_permission_checker(db)
        permission_service = permission_service or PermissionService(
            db,
            permission_repository=PermissionRepository(db),
            project_repository=ProjectRepository(db),
            auto_commit=False,
        )
        original_team_init(
            self,
            db,
            team_repository=team_repository,
            permission_checker=permission_checker,
            permission_service=permission_service,
        )

    def _project_init_compat(
        self,
        db: AsyncSession,
        project_repository: ProjectRepository | None = None,
        permission_service: PermissionService | None = None,
        permission_checker: PermissionChecker | None = None,
        team_repository: TeamRepository | None = None,
        scalars_service=None,
        object_storage_client=None,
    ) -> None:
        project_repository = project_repository or ProjectRepository(db)
        permission_service = permission_service or PermissionService(
            db,
            permission_repository=PermissionRepository(db),
            project_repository=ProjectRepository(db),
            auto_commit=False,
        )
        permission_checker = permission_checker or PermissionChecker(db, permission_service)
        team_repository = team_repository or TeamRepository(db)
        original_project_init(
            self,
            db,
            project_repository=project_repository,
            permission_service=permission_service,
            permission_checker=permission_checker,
            team_repository=team_repository,
            scalars_service=scalars_service,
            object_storage_client=object_storage_client,
        )

    def _dashboard_init_compat(
        self,
        session: AsyncSession,
        permission_checker: PermissionChecker | None = None,
        experiment_repository: ExperimentRepository | None = None,
        hypothesis_repository: HypothesisRepository | None = None,
    ) -> None:
        permission_checker = permission_checker or _make_permission_checker(session)
        experiment_repository = experiment_repository or ExperimentRepository(session)
        hypothesis_repository = hypothesis_repository or HypothesisRepository(session)
        original_dashboard_init(
            self,
            session,
            permission_checker=permission_checker,
            experiment_repository=experiment_repository,
            hypothesis_repository=hypothesis_repository,
        )

    async def _api_token_repo_create_compat(
        self, token
    ):
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token

    async def _api_token_repo_update_compat(
        self, token
    ):
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        return token

    monkeypatch.setattr(PermissionService, "__init__", _permission_init_compat)
    monkeypatch.setattr(PermissionChecker, "__init__", _permission_checker_init_compat)
    monkeypatch.setattr(ApiTokenService, "__init__", _api_token_init_compat)
    monkeypatch.setattr(ExperimentService, "__init__", _experiment_init_compat)
    monkeypatch.setattr(HypothesisService, "__init__", _hypothesis_init_compat)
    monkeypatch.setattr(MetricService, "__init__", _metric_init_compat)
    monkeypatch.setattr(TeamService, "__init__", _team_init_compat)
    monkeypatch.setattr(ProjectService, "__init__", _project_init_compat)
    monkeypatch.setattr(DashboardService, "__init__", _dashboard_init_compat)
    monkeypatch.setattr(ApiTokenRepository, "create", _api_token_repo_create_compat)
    monkeypatch.setattr(ApiTokenRepository, "update", _api_token_repo_update_compat)
