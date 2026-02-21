import contextlib
import logging


@contextlib.contextmanager
def disable_httpx_logging():
    """Context manager to temporarily disable httpx logging."""
    # Get the httpx logger and save its current state
    httpx_logger = logging.getLogger("httpx")
    original_level = httpx_logger.level
    original_disabled_status = httpx_logger.disabled

    try:
        # Set the level to CRITICAL + 1 (effectively OFF) or set disabled to True
        httpx_logger.setLevel(logging.ERROR)
        yield
    finally:
        # Restore the original level and disabled status
        httpx_logger.setLevel(original_level)
        httpx_logger.disabled = original_disabled_status
