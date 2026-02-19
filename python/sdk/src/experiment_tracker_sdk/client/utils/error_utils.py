import json
import logging

from httpx import Response


def log_error_response(response: Response, logger: logging.Logger) -> None:
    try:
        data = response.json()
    except json.JSONDecodeError:
        data = response.text
    logger.error(
        f"error_response: {data}",
        extra={"path": response.request.url, "error": data},
    )
