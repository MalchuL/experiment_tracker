"""
Pytest configuration and fixtures for testing.
"""

import os
import sys
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
from domain.team.teams.repository import TeamRepository
from db.utils import build_async_database_url

# Use in-memory SQLite database for tests by default
DEFAULT_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_DATABASE_URL = (
    os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    or DEFAULT_TEST_DATABASE_URL
)


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
            # Start a transaction manually (don't use begin() context manager as it commits)
            # Type ignore because AsyncSessionTransaction is compatible for our use case
            transaction = await session.begin()  # type: ignore[assignment]
            try:
                yield session
            finally:
                # Always rollback to clean up test data
                # This ensures test isolation
                await transaction.rollback()


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
