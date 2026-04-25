import json
import logging
import queue
import threading
from dataclasses import dataclass
import traceback
from typing import Any, Optional

from .request_types import FileUploadSpec
from .utils import log_error_response
import httpx
from .utils.logging import disable_httpx_logging

logger = logging.getLogger("experiment_tracker_sdk")


@dataclass(frozen=True)
class RequestItem:
    method: str
    path: str
    json: Optional[dict[str, Any]] = None
    form_data: Optional[dict[str, Any]] = None
    files: Optional[dict[str, FileUploadSpec]] = None
    params: Optional[dict[str, Any]] = None


class RequestQueue:
    def __init__(
        self,
        client: httpx.Client,
        max_queue_size: int = 1000,
        poll_interval: float = 0.5,
    ):
        """Create a background queue for async-like request logging.

        Args:
            client: httpx client used to send requests.
            max_queue_size: Max items buffered before blocking.
            poll_interval: Poll interval in seconds for worker thread.
        """
        self._client = client
        self._queue: queue.Queue[RequestItem] = queue.Queue(maxsize=max_queue_size)
        self._poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def enqueue(self, item: RequestItem) -> None:
        """Enqueue a request item, blocking if the queue is full.

        Args:
            item: RequestItem with method/path/payload.
        """
        if self._queue.full():
            logger.warning("request_queue_full_blocking", extra={"path": item.path})
            # Block until the queue drains to avoid dropping requests.
            self._queue.join()
        self._queue.put(item, block=True)

    def flush(self, timeout: Optional[float] = None) -> None:
        """Wait for all queued requests to finish sending.

        Args:
            timeout: Reserved for future timeout handling.
        """
        self._queue.join()

    def close(self) -> None:
        """Stop the background thread after flushing remaining items."""
        self._stop_event.set()
        self.flush()
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        """Worker loop that sends queued requests."""
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                item = self._queue.get(timeout=self._poll_interval)
            except queue.Empty:
                continue
            try:
                with disable_httpx_logging():
                    if item.json is not None and (
                        item.form_data is not None or item.files is not None
                    ):
                        raise ValueError(
                            "RequestItem cannot contain both json and data/files payloads"
                        )

                    files_payload: dict[str, tuple[str, bytes, str]] | None = None
                    if item.files is not None:
                        # TODO: Test this with actual files.
                        files_payload = {
                            key: (
                                value.filename,
                                value.content,
                                value.content_type,
                            )
                            for key, value in item.files.items()
                        }

                    response = self._client.request(
                        item.method,
                        item.path,
                        json=item.json,
                        data=item.form_data,
                        files=files_payload,
                        params=item.params,
                    )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                log_error_response(exc.response, logger)
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
            finally:
                self._queue.task_done()
