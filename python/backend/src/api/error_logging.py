import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


LOGGER_NAME = "experiment_tracker.api"


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )


def register_exception_handlers(app: FastAPI, *, log_stacktrace: bool) -> None:
    logger = logging.getLogger(LOGGER_NAME)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.error(
            "HTTPException %s %s -> %s detail=%r",
            request.method,
            request.url.path,
            exc.status_code,
            exc.detail,
            stack_info=log_stacktrace,
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors: Any = exc.errors()
        logger.warning(
            "RequestValidationError %s %s -> 422 errors=%s",
            request.method,
            request.url.path,
            errors,
            stack_info=log_stacktrace,
        )
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "UnhandledException %s %s -> 500",
            request.method,
            request.url.path,
            exc_info=log_stacktrace,
        )
        if not log_stacktrace:
            logger.error("%s: %s", type(exc).__name__, exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
