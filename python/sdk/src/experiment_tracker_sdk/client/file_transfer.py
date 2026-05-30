"""Batch upload/download against one endpoint with per-item query parameters."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar

import httpx

from experiment_tracker_sdk.client.request_types import (
    ApiRequestSpec,
    FileDownloadItem,
    FileDownloadResponse,
    FileDownloadToPathItem,
    FileUploadItem,
    FileUploadSpec,
    MethodT,
)
from experiment_tracker_sdk.client.transport.executor import HttpRequestExecutor
from experiment_tracker_sdk.client.transport.options import RequestOptions, resolve_stream
from experiment_tracker_sdk.client.utils.downloading import dump_binary_content_to_path
from experiment_tracker_sdk.client.utils.transfer_progress import batch_items_progress

T = TypeVar("T")


def _run_batch(
    items: Sequence[Any],
    *,
    desc: str,
    options: RequestOptions,
    label_for: Callable[[Any, int], str],
    process: Callable[[Any, int, RequestOptions], T],
) -> list[T]:
    """Run ``process`` for each item, optionally showing a batch-level tqdm counter.

    When ``options.verbose`` is ``True``, an outer bar tracks completed files
    (position 0) and each item gets ``progress_position=1`` for its byte bar.
    """
    batch_bar = (
        batch_items_progress(total=len(items), desc=desc, disable=False)
        if options.verbose and items
        else None
    )
    results: list[T] = []
    try:
        for index, item in enumerate(items):
            if batch_bar is not None:
                batch_bar.set_postfix_str(label_for(item, index))
            item_options = options.with_progress(
                position=1 if options.verbose else None,
                leave=False,
            )
            results.append(process(item, index, item_options))
            if batch_bar is not None:
                batch_bar.update(1)
    finally:
        if batch_bar is not None:
            batch_bar.close()
    return results


class FileTransferService:
    """Batch file I/O built on :class:`~experiment_tracker_sdk.client.transport.executor.HttpRequestExecutor`.

    Each item becomes an :class:`~experiment_tracker_sdk.client.request_types.ApiRequestSpec`
    with the same ``endpoint`` and ``method`` but different ``query_params`` (and
    optional form fields for uploads).
    """

    def __init__(self, executor: HttpRequestExecutor) -> None:
        self._executor = executor

    def upload_files_batch(
        self,
        http_client: httpx.Client,
        endpoint: str,
        items: Sequence[FileUploadItem],
        method: MethodT = "POST",
        *,
        options: RequestOptions | None = None,
    ) -> list[dict[str, Any]]:
        """Upload many files through one endpoint, varying query params per item.

        Args:
            http_client: httpx client used for each upload.
            endpoint: Shared path relative to the client base URL.
            items: Per-file params, bytes, and optional form fields.
            method: HTTP method applied to every item (default ``POST``).
            options: When ``verbose=True``, show batch and per-file tqdm bars.

        Returns:
            Parsed JSON response bodies, one per item in order.
        """
        opts = options or RequestOptions()

        def process(item: FileUploadItem, _index: int, item_options: RequestOptions) -> dict[str, Any]:
            spec = ApiRequestSpec(
                method=method,
                endpoint=endpoint,
                query_params=item.params,
                form_data=item.form_data,
                files={
                    "file": FileUploadSpec(
                        filename=item.filename,
                        content=item.content,
                        content_type=item.content_type,
                    )
                },
            )
            item_opts = item_options.with_progress(
                desc=f"Upload {item.label or item.filename}",
                verbose=opts.verbose,
            )
            result = self._executor.execute(http_client, spec, item_opts)
            if isinstance(result, dict):
                return result
            raise TypeError("upload_files_batch expected JSON dict response")

        return _run_batch(
            items,
            desc="Upload batch",
            options=opts,
            label_for=lambda item, _i: item.label or item.filename,
            process=process,
        )

    def download_files_batch(
        self,
        http_client: httpx.Client,
        endpoint: str,
        items: Sequence[FileDownloadItem],
        method: MethodT = "GET",
        *,
        options: RequestOptions | None = None,
    ) -> list[FileDownloadResponse]:
        """Download many files from one endpoint with per-item query parameters.

        When ``options.verbose`` is ``True``, streaming is enabled automatically
        for each item so byte-level progress bars can update as chunks arrive.

        Returns:
            Download responses in the same order as ``items``.
        """
        opts = options or RequestOptions()
        stream = resolve_stream(opts, is_download=True)

        def process(
            item: FileDownloadItem, index: int, item_options: RequestOptions
        ) -> FileDownloadResponse:
            label = item.label or (
                item.params.get("name") if item.params else None
            )
            progress_desc = (
                f"Download {label}"
                if isinstance(label, str)
                else f"Download {index + 1}/{len(items)}"
            )
            spec = ApiRequestSpec(
                method=method,
                endpoint=endpoint,
                query_params=item.params,
                response_model=FileDownloadResponse,
            )
            item_opts = item_options.with_progress(
                desc=progress_desc,
                verbose=opts.verbose,
                stream=stream,
            )
            result = self._executor.execute(http_client, spec, item_opts)
            if not isinstance(result, FileDownloadResponse):
                raise TypeError("download_files_batch expected FileDownloadResponse")
            return result

        return _run_batch(
            items,
            desc="Download batch",
            options=opts,
            label_for=lambda item, index: item.label or str(index + 1),
            process=process,
        )

    def download_files_batch_to_paths(
        self,
        http_client: httpx.Client,
        endpoint: str,
        items: Sequence[FileDownloadToPathItem],
        method: MethodT = "GET",
        *,
        options: RequestOptions | None = None,
    ) -> list[Path]:
        """Download many files and write each one to a local path.

        Combines streaming download semantics with
        :func:`~experiment_tracker_sdk.client.utils.downloading.dump_binary_content_to_path`.
        If an ``output_path`` is a directory, the filename from
        ``Content-Disposition`` is appended.

        Returns:
            Resolved filesystem paths where each file was written.
        """
        opts = options or RequestOptions()
        stream = resolve_stream(opts, is_download=True)

        def process(
            item: FileDownloadToPathItem, _index: int, item_options: RequestOptions
        ) -> Path:
            spec = ApiRequestSpec(
                method=method,
                endpoint=endpoint,
                query_params=item.params,
                response_model=FileDownloadResponse,
            )
            item_opts = item_options.with_progress(
                desc=item.label or Path(item.output_path).name,
                verbose=opts.verbose,
                stream=stream,
            )
            result = self._executor.execute(http_client, spec, item_opts)
            if not isinstance(result, FileDownloadResponse):
                raise TypeError(
                    "download_files_batch_to_paths expected FileDownloadResponse"
                )
            return dump_binary_content_to_path(
                result.content, item.output_path, result.filename
            )

        return _run_batch(
            items,
            desc="Download batch",
            options=opts,
            label_for=lambda item, _i: item.label or Path(item.output_path).name,
            process=process,
        )
