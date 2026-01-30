import logging
import queue
import threading
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger("experiment_tracker_sdk")


@dataclass(frozen=True)
class RequestItem:
    method: str
    path: str
    json: Optional[dict[str, Any]] = None
    params: Optional[dict[str, Any]] = None


class RequestQueue:
    def __init__(
        self,
        client: httpx.Client,
        max_queue_size: int = 1000,
        poll_interval: float = 0.5,
    ):
        self._client = client
        self._queue: queue.Queue[RequestItem] = queue.Queue(maxsize=max_queue_size)
        self._poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def enqueue(self, item: RequestItem) -> None:
        if self._queue.full():
            logger.warning("request_queue_full_blocking", extra={"path": item.path})
            # Block until the queue drains to avoid dropping requests.
            self._queue.join()
        self._queue.put(item, block=True)

    def flush(self, timeout: Optional[float] = None) -> None:
        self._queue.join()

    def close(self) -> None:
        self._stop_event.set()
        self.flush()
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                item = self._queue.get(timeout=self._poll_interval)
            except queue.Empty:
                continue
            try:
                response = self._client.request(
                    item.method, item.path, json=item.json, params=item.params
                )
                response.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "request_failed",
                    extra={"path": item.path, "error": str(exc)},
                )
            finally:
                self._queue.task_done()
