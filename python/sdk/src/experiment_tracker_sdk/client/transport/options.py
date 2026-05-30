"""Per-request options: tqdm progress bars and streaming download behavior."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class RequestOptions:
    """Options passed to :meth:`~experiment_tracker_sdk.client.client.ExperimentTrackerClient.request`.

    Attributes:
        verbose: When ``True``, show tqdm byte progress during multipart uploads
            and streaming downloads. Does not affect ordinary JSON requests.
        stream: Download-only. ``None`` (default) auto-enables streaming when
            ``verbose`` is ``True`` on a download; ``True``/``False`` force
            streaming or buffered mode.
        progress_desc: tqdm label override (batch transfers set this per item).
        progress_position: tqdm ``position`` for nested bars (batch uses ``1``
            for the per-file bar under the outer file counter).
        progress_leave: Whether the tqdm bar stays on screen after completion.
    """

    verbose: bool = False
    stream: bool | None = None
    progress_desc: str | None = None
    progress_position: int | None = None
    progress_leave: bool = True

    def with_progress(
        self,
        *,
        desc: str | None = None,
        position: int | None = None,
        leave: bool | None = None,
        verbose: bool | None = None,
        stream: bool | None = None,
    ) -> RequestOptions:
        """Return a copy with progress/stream fields overridden.

        Used by batch transfer to stack an outer file counter (position 0) and
        an inner byte bar (position 1) without mutating the caller's options.
        """
        return replace(
            self,
            verbose=self.verbose if verbose is None else verbose,
            stream=self.stream if stream is None else stream,
            progress_desc=desc if desc is not None else self.progress_desc,
            progress_position=position if position is not None else self.progress_position,
            progress_leave=self.progress_leave if leave is None else leave,
        )


def resolve_stream(options: RequestOptions, *, is_download: bool) -> bool:
    """Decide whether the response body is read chunk-by-chunk.

    Explicit ``options.stream`` always wins. When ``stream`` is ``None``, verbose
    mode enables streaming only for downloads (so tqdm can update as chunks
    arrive). Uploads never use this helper to stream the response body.
    """
    if options.stream is not None:
        return options.stream
    return options.verbose if is_download else False
