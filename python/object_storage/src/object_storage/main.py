from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from object_storage.api import router as api_router
from object_storage.config import get_settings
from object_storage.db import create_db_and_tables
from object_storage.storage import get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare database tables and ensure the CAS bucket exists on startup."""

    await create_db_and_tables()
    storage = get_storage()
    await anyio.to_thread.run_sync(storage.ensure_bucket)
    yield


def create_app() -> FastAPI:
    """Create the FastAPI application configured for the CAS service."""

    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(map(str.strip, settings.allowed_origins.split(","))),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()


def run() -> None:
    """Run the CAS service with a production-friendly Uvicorn entrypoint."""

    import uvicorn

    uvicorn.run(
        "object_storage.main:app",
        host="0.0.0.0",
        port=8010,
        reload=False,
    )
