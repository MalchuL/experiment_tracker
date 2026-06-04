"""Build httpx multipart file parts, optionally wrapped for upload progress bars."""

from __future__ import annotations

from typing import Any

from experiment_tracker_sdk.client.request_types import FileUploadSpec
from experiment_tracker_sdk.client.utils.transfer_progress import (
    UploadMultipartBody,
    UploadMultipartFilePart,
    progress_file_reader,
    progress_stream_reader,
)


def close_progress_bars(bars: list[Any]) -> None:
    """Release tqdm UI resources after an upload request finishes."""
    for bar in bars:
        bar.close()


def build_multipart_files(
    files: dict[str, FileUploadSpec] | None,
    *,
    verbose: bool = False,
    progress_desc_prefix: str = "Upload",
    progress_position: int | None = None,
    progress_leave: bool = True,
) -> tuple[dict[str, UploadMultipartFilePart] | None, list[Any]]:
    """Convert SDK file specs into the tuple shape httpx expects for multipart uploads.

    Returns ``(httpx_files, progress_bars)``. The caller must close
    ``progress_bars`` after the HTTP request completes.

    When ``verbose`` is ``False``, each part body is passed through unchanged.
    When ``verbose`` is ``True``, bytes or binary file objects are wrapped so
    httpx reads in slices and tqdm can update.
    """
    if files is None:
        return None, []

    httpx_files: dict[str, UploadMultipartFilePart] = {}
    progress_bars: list[Any] = []

    for field_name, spec in files.items():
        body: UploadMultipartBody = spec.content
        if verbose:
            if isinstance(spec.content, bytes):
                body, bar = progress_file_reader(
                    spec.content,
                    desc=f"{progress_desc_prefix} {spec.filename}",
                    position=progress_position,
                    leave=progress_leave,
                )
            else:
                body, bar = progress_stream_reader(
                    spec.content,
                    desc=f"{progress_desc_prefix} {spec.filename}",
                    total=spec.size,
                    position=progress_position,
                    leave=progress_leave,
                )
            progress_bars.append(bar)
        httpx_files[field_name] = (spec.filename, body, spec.content_type)

    return httpx_files, progress_bars
