from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from typing import Any, BinaryIO, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel

MethodT = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
FileUploadContent: TypeAlias = bytes | BinaryIO


@dataclass(frozen=True)
class FileUploadSpec:
    """File upload specification.

    Args:
        content: Raw bytes or a binary file object to upload.
        filename: Filename sent with the multipart part.
        content_type: MIME type of the file to upload.
        size: Optional byte size for stream progress bars.
    """

    content: FileUploadContent
    filename: str
    content_type: str = "application/octet-stream"
    size: int | None = None


@dataclass(frozen=True)
class FileUploadItem:
    """One file in a batched upload (same endpoint/method, per-item params)."""

    params: dict[str, Any]
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    form_data: dict[str, Any] | None = None
    label: str | None = None


@dataclass(frozen=True)
class FileDownloadItem:
    """One file in a batched download (same endpoint/method, per-item params)."""

    params: dict[str, Any] | None = None
    label: str | None = None


@dataclass(frozen=True)
class FileDownloadToPathItem:
    """Batched download with a fixed local destination path."""

    output_path: str
    params: dict[str, Any] | None = None
    label: str | None = None


@dataclass(frozen=True)
class FileDownloadResponse:
    """Response wrapper for binary file downloads.

    Args:
        content: Raw file bytes, a BytesIO stream, or a streamed bytes iterator.
        filename: Filename from the Content-Disposition header, or None if absent.
        content_type: MIME type from the Content-Type header.
    """

    content: bytes | BytesIO | Iterator[bytes]
    filename: str | None
    content_type: str = "application/octet-stream"


ResponseT = TypeVar("ResponseT", bound=BaseModel | FileDownloadResponse)


@dataclass(frozen=True)
class ApiRequestSpec(Generic[ResponseT]):
    """API request specification.

    Args:
        method: HTTP method to use.
        endpoint: API endpoint to call like "/api/v1/experiments".
        request_payload: JSON payload to send in the request body like
            {"name": "John Doe"}.
        form_data: Form data to send in the request body, used for multipart
            requests.
        files: Files to send in the request body, used for multipart/form-data requests.
        response_model: Pydantic model or file download response to parse the
            response body into.
        query_params: Query parameters to send in the request URL.
    """

    method: MethodT
    endpoint: str
    request_payload: dict[str, Any] | BaseModel | None = None
    form_data: dict[str, Any] | None = None
    files: dict[str, FileUploadSpec] | None = None
    response_model: type[ResponseT] | type[FileDownloadResponse] | None = None
    query_params: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate that a request spec uses only one payload encoding.

        Args:
            None. The dataclass fields are inspected after initialization.

        Returns:
            None. Raises ``ValueError`` when JSON payloads are combined with
            form-data or file uploads.
        """
        has_json_payload = self.request_payload is not None
        has_form_payload = self.form_data is not None or self.files is not None
        # JSON and form payload are mutually exclusive.
        if has_json_payload and has_form_payload:
            raise ValueError(
                "ApiRequestSpec cannot contain both request_payload (json) "
                "and form_data/files (multipart/form-data)"
            )
