"""Create and configure the MLTools FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from mltools.api.routes import router
from mltools.config.settings import get_settings
from mltools.db.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize service resources for the FastAPI application lifespan.

    Args:
        app: FastAPI application entering its startup/shutdown lifecycle.

    Yields:
        None: Control returns to FastAPI after database tables are initialized.
    """
    await create_db_and_tables()
    yield


def create_app() -> FastAPI:
    """Build the configured MLTools FastAPI application.

    Returns:
        FastAPI: Application with the internal MLTools router and startup lifespan.
    """
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.12.0", lifespan=lifespan)
    app.include_router(router, prefix=settings.api_prefix)
    return app


app = create_app()
"""FastAPI application entry point for the MLTools microservice.

The application exposes trusted internal routes used by the main backend and
initializes the MLTools relational schema during process startup.
"""
