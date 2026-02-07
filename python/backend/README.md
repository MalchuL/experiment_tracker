# Experiment Tracker Backend

## Installation

```bash
cd python/backend
# Install all dependencies including dev dependencies (pytest, etc.)
uv sync --extra dev
```

## Running the Server

```bash
uv run uvicorn api.main:app --reload --port 8001
```

## Scalars Service Integration

This backend proxies scalar logging/reading to the scalars microservice.

Set the scalars service base URL in `.env` (defaults to `http://127.0.0.1:8001/api`):

```
SCALARS_SERVICE_URL=http://127.0.0.1:8001/api
```

If you run both services locally, use different ports (for example, start the backend on `8000`).

## Clean Database
`psql "postgresql://USER:PASSWORD@HOST:PORT/your_db_name"`

-- then run:
`DROP SCHEMA public CASCADE;`
`CREATE SCHEMA public;`

## Database Setup

### For Development

The backend uses SQLAlchemy with async support. By default, it uses SQLite for development.

1. **SQLite (Default)**: No setup required. The database file will be created automatically at `./data.db`.

2. **PostgreSQL (Recommended for Production)**:
   - Install PostgreSQL and create a database:
     ```bash
     createdb experiment_tracker
     ```
   - Set the `DATABASE_URL` environment variable:
     ```bash
     export DATABASE_URL="postgresql://username:password@localhost:5432/experiment_tracker"
     ```
   - Or use a `.env` file:
     ```
     DATABASE_URL=postgresql://username:password@localhost:5432/experiment_tracker
     ```

3. **Initialize the database schema**:
   The tables will be created automatically on first run, or you can run:
   ```python
   from db.database import create_db_and_tables
   await create_db_and_tables()
   ```

### For Testing

The test suite uses an in-memory SQLite database by default, which requires no setup. However, for more realistic testing, you can use a PostgreSQL test database.

#### Option 1: In-Memory SQLite (Default - No Setup Required)

Tests run against an in-memory SQLite database. No database setup is needed:

```bash
uv run pytest
```

#### Option 2: PostgreSQL Test Database (Recommended for CI/CD)

For testing against PostgreSQL (more realistic, catches PostgreSQL-specific issues):

1. **Create a test database**:
   ```bash
   createdb experiment_tracker_test
   ```

2. **Set the test database URL**:
   ```bash
   export TEST_DATABASE_URL="postgresql+asyncpg://username:password@localhost:5432/experiment_tracker_test"
   ```

3. **Run tests**:
   ```bash
   uv run pytest
   ```

   The test fixtures will automatically:
   - Create all tables before tests
   - Roll back all changes after each test (using transactions)
   - Drop all tables after the test session

#### Option 3: SQLite File Database

You can also use a SQLite file database for tests:

```bash
export TEST_DATABASE_URL="sqlite+aiosqlite:///./test.db"
uv run pytest
```

**Note**: Make sure to add `test.db` to your `.gitignore` file.

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_teams_repository.py

# Run a specific test
uv run pytest tests/test_teams_repository.py::TestTeamRepository::test_create_team

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## Test Database Best Practices

1. **Isolation**: Each test runs in a transaction that is rolled back, ensuring test isolation.

2. **Fixtures**: Use the provided fixtures (`db_session`, `test_user`, `test_team`, etc.) to set up test data.

3. **Cleanup**: The test fixtures automatically clean up after each test, so you don't need to manually delete test data.

4. **CI/CD**: For continuous integration, use PostgreSQL with the `TEST_DATABASE_URL` environment variable set in your CI configuration.

## Project Structure

```
src/
├── api/              # FastAPI application and routes
├── config/           # Configuration and settings
├── db/               # Database connection and session management
├── domain/           # Domain logic and repositories
│   ├── team/        # Team domain
│   ├── projects/    # Project domain
│   └── ...
├── lib/              # Shared libraries
└── models.py         # SQLAlchemy models
```