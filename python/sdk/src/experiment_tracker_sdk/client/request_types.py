from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Generic, Iterator, Literal, TypeVar, Union

from pydantic import BaseModel

MethodT = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]


@dataclass(frozen=True)
class FileUploadSpec:
    """File upload specification.

    Args:
        filename: Name of the file to upload.
        content: Content of the file to upload.
        content_type: MIME type of the file to upload.
    """

    content: bytes
    filename: str
    content_type: str = "application/octet-stream"


@dataclass(frozen=True)
class FileDownloadResponse:
    """Response wrapper for binary file downloads.

    Args:
        content: Raw file bytes, a BytesIO stream, or a streamed bytes iterator.
        filename: Filename from the Content-Disposition header, or None if absent.
        content_type: MIME type from the Content-Type header.
    """

    content: Union[bytes, BytesIO, Iterator[bytes]]
    filename: str | None
    content_type: str = "application/octet-stream"


ResponseT = TypeVar("ResponseT", bound=BaseModel | FileDownloadResponse)


@dataclass(frozen=True)
class ApiRequestSpec(Generic[ResponseT]):
    """API request specification.

    Args:
        method: HTTP method to use.
        endpoint: API endpoint to call like "/api/v1/experiments".
        request_payload: JSON payload to send in the request body like {"name": "John Doe"}.
        form_data: Form data to send in the request body, used for multipart/form-data requests.
        files: Files to send in the request body, used for multipart/form-data requests.
        response_model: Pydantic model or file download response to parse the response body into.
        query_params: Query parameters to send in the request URL for /api/v1/experiments?name=John Doe.
    """

    method: MethodT
    endpoint: str
    request_payload: dict[str, Any] | BaseModel | None = None
    form_data: dict[str, Any] | None = None
    files: dict[str, FileUploadSpec] | None = None
    response_model: type[ResponseT] | None = None
    query_params: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        has_json_payload = self.request_payload is not None
        has_form_payload = self.form_data is not None or self.files is not None
        # JSON and form payload are mutually exclusive.
        if has_json_payload and has_form_payload:
            raise ValueError(
                "ApiRequestSpec cannot contain both request_payload (json) and form_data/files (multipart/form-data)"
            )
