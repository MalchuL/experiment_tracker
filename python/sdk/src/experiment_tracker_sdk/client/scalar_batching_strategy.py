from threading import RLock, Timer
from uuid import UUID

from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.domain.scalars.dto import LogScalarRequest

SCALAR_BATCH_MAX_STEPS = 256
SCALAR_BATCH_MAX_SECONDS = 5.0


class BatchedScalarLoggingStrategy:
    """Groups scalar rows and sends them through the existing request queue."""

    def __init__(
        self,
        *,
        experiment_id: str | UUID,
        registry: APIRequestsRegistry,
        request_client: ExperimentTrackerClient,
        max_steps: int = SCALAR_BATCH_MAX_STEPS,
        max_seconds: float = SCALAR_BATCH_MAX_SECONDS,
    ):
        self.experiment_id = experiment_id
        self.registry = registry
        self.request_client = request_client
        self.max_steps = max_steps
        self.max_seconds = max_seconds

        # Step currently being grouped into one scalar row.
        self._current_scalar_step = 0
        # Scalar values collected for _current_scalar_step.
        self._current_step_scalars: dict[str, float] = {}
        # Completed step rows waiting to be sent as one batch request.
        self._scalar_rows_buffer: list[LogScalarRequest] = []
        # Protects scalar buffers from concurrent add_scalar and timer flushes.
        self._scalar_buffer_lock = RLock()
        # Timer that automatically flushes scalar buffers after max batch age.
        self._scalar_flush_timer: Timer | None = None

    def add_scalar(self, tag: str, scalar_value: float, global_step: int) -> None:
        """Add one scalar value and queue a batch if the row limit is reached."""
        with self._scalar_buffer_lock:
            if global_step == self._current_scalar_step:
                # One row can contain multiple scalar columns for the same step.
                self._current_step_scalars[tag] = scalar_value
            else:
                # Complete the previous step row before starting a new one.
                self._move_current_step_to_buffer_locked()
                self._current_scalar_step = global_step
                self._current_step_scalars = {tag: scalar_value}

            scalars = []
            if len(self._scalar_rows_buffer) >= self.max_steps:
                # The batch reached the row limit. Drain only completed rows;
                # This cancels the timer and returns the completed rows.
                scalars = self._drain_scalar_buffer_locked(include_current_step=False)

            # Start the timer after the optional drain. Only if no active timer is running!!!
            self._start_scalar_flush_timer_locked()
        # Send the buffered scalars to the API.
        if scalars:
            self._queue_scalar_batch(scalars)

    def flush(self) -> None:
        """Queue all buffered scalar rows immediately."""
        with self._scalar_buffer_lock:
            scalars = self._drain_scalar_buffer_locked(include_current_step=True)
            self._current_scalar_step = 0
        self._queue_scalar_batch(scalars)

    def _move_current_step_to_buffer_locked(self) -> None:
        """Move the current step's grouped scalar values into the batch buffer."""
        if not self._current_step_scalars:
            return
        self._scalar_rows_buffer.append(
            LogScalarRequest(
                scalars=dict(self._current_step_scalars),
                step=self._current_scalar_step,
            )
        )
        self._current_step_scalars = {}

    def _drain_scalar_buffer_locked(
        self, *, include_current_step: bool
    ) -> list[LogScalarRequest]:
        """Return buffered scalar rows and clear the buffer."""
        if include_current_step:
            self._move_current_step_to_buffer_locked()
        if not self._scalar_rows_buffer:
            return []
        scalars = list(self._scalar_rows_buffer)
        self._scalar_rows_buffer = []
        self._cancel_scalar_flush_timer_locked()
        return scalars

    def _queue_scalar_batch(self, scalars: list[LogScalarRequest]) -> None:
        """Queue scalar steps as one batch request."""
        if not scalars:
            return
        self.request_client.queued_request(
            self.registry.scalars.log_scalars_batch(
                self.experiment_id,
                scalars,
            )
        )

    def _flush_scalar_buffer_after_timeout(self) -> None:
        """Queue buffered scalars when the five-second timer fires."""
        with self._scalar_buffer_lock:
            self._scalar_flush_timer = None
            scalars = self._drain_scalar_buffer_locked(include_current_step=True)
        self._queue_scalar_batch(scalars)

    def _start_scalar_flush_timer_locked(self) -> None:
        """Start the timer that flushes buffered scalars after max_seconds."""
        if self._scalar_flush_timer is not None:
            return
        if not self._current_step_scalars and not self._scalar_rows_buffer:
            return
        # The timer may run on another thread, so it only drains data while
        # holding the same lock used by add_scalar and flush.
        self._scalar_flush_timer = Timer(
            self.max_seconds,
            self._flush_scalar_buffer_after_timeout,
        )
        self._scalar_flush_timer.daemon = True
        self._scalar_flush_timer.start()

    def _cancel_scalar_flush_timer_locked(self) -> None:
        """Cancel the active scalar timeout timer while lock is held."""
        if self._scalar_flush_timer is None:
            return
        self._scalar_flush_timer.cancel()
        self._scalar_flush_timer = None
