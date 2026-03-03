from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.api import router as api_router
from api.error_logging import configure_logging, register_exception_handlers
from config.settings import get_settings
from db.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="ML Experiment Tracker API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(map(str.strip, settings.allowed_origins.split(","))),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    register_exception_handlers(app, log_stacktrace=settings.log_stacktrace)
    return app


app = create_app()
