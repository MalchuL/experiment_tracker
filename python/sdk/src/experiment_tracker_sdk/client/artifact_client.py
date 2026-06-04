"""High-level artifact upload and download API.

Builds :class:`~experiment_tracker_sdk.client.request_types.ApiRequestSpec`
instances from :class:`~experiment_tracker_sdk.client.api_registry.APIRequestsRegistry`
and delegates HTTP I/O to
:class:`~experiment_tracker_sdk.client.client.ExperimentTrackerClient`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, TypeVar, cast

from pydantic import BaseModel, Field

from experiment_tracker_sdk.client.domain.project_artifacts.dto import (
    CheckProjectArtifactsResponse,
)
from experiment_tracker_sdk.client.request_types import FileUploadContent
from experiment_tracker_sdk.client.utils.downloading import dump_binary_content_to_path

from .api_registry import APIRequestsRegistry
from .client import ExperimentTrackerClient
from .domain.experiment_artifacts.dto import ArtifactType, LogArtifactAtStepResponse
from .request_types import ApiRequestSpec, FileDownloadResponse, FileUploadSpec
from .transport.options import RequestOptions

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class BlobUploadResult(BaseModel):
    """Result of a project content-addressed artifact upload."""

    status: Literal["ok", "error"] = Field(description="Status of the upload.")
    detail: Literal["exists", "uploaded", "error"] = Field(
        description="Detail of the upload."
    )
    hash: str = Field(description="Hash of the uploaded blob.")
    upload: dict[str, Any] = Field(description="Upload result.")


class ArtifactClient:
    """Upload and download binary artifacts through the API.

    Used by :class:`~experiment_tracker_sdk.exp_tracker.ExpTracker` for step
    images/text and final artifacts. Upload methods accept ``verbose`` for tqdm
    byte progress; download methods accept ``stream`` for chunked I/O and
    optional ``output_path`` to write directly to disk.
    """

    def __init__(
        self,
        registry: APIRequestsRegistry,
        request_client: ExperimentTrackerClient,
    ) -> None:
        self.registry = registry
        self.request_client = request_client

    def _request(
        self,
        spec: ApiRequestSpec[ResponseT],
        *,
        options: RequestOptions | None = None,
    ) -> ResponseT:
        """Run a spec that returns a JSON/Pydantic body."""
        result = self.request_client.request(spec, options=options)
        return cast(ResponseT, result)

    def _download(
        self,
        spec: ApiRequestSpec[Any],
        *,
        options: RequestOptions | None = None,
        output_path: str | Path | None = None,
    ) -> FileDownloadResponse | Path:
        """Run a download spec; optionally persist bytes to ``output_path``."""
        result = self.request_client.request(spec, options=options)
        download = cast(FileDownloadResponse, result)
        if output_path is None:
            return download
        return dump_binary_content_to_path(
            download.content, output_path, download.filename
        )

    # --- Project artifacts (CAS) ---

    def check_project_artifacts(
        self, project_id: str, hashes: list[str]
    ) -> CheckProjectArtifactsResponse:
        """Return which content hashes are missing from project storage."""
        return self._request(
            self.registry.project_artifacts.check_project_artifacts(project_id, hashes),
        )

    def upload_project_artifact(
        self,
        project_id: str,
        filename: str,
        content: FileUploadContent,
        content_type: str,
        *,
        artifact_hash: str | None = None,
        size: int | None = None,
        verbose: bool = False,
    ) -> BlobUploadResult:
        """Upload content into project CAS when the hash is not already stored.

        Skips the upload HTTP call when the SHA-256 hash already exists.
        """
        from experiment_tracker_shared import compute_sha256_hexdigest  # type: ignore

        if artifact_hash is None:
            if not isinstance(content, bytes):
                raise ValueError(
                    "artifact_hash is required when uploading file-like content"
                )
            artifact_hash = compute_sha256_hexdigest(content)
        check_result = self.check_project_artifacts(project_id, [artifact_hash])
        if artifact_hash not in set(check_result.missing):
            return BlobUploadResult(
                status="ok", detail="exists", hash=artifact_hash, upload={}
            )

        file_spec = FileUploadSpec(
            filename=filename,
            content=content,
            content_type=content_type,
            size=size,
        )
        spec = self.registry.project_artifacts.upload_project_artifact(
            project_id=project_id,
            artifact_hash=artifact_hash,
            file=file_spec,
        )
        upload_result = self._request(spec, options=RequestOptions(verbose=verbose))
        return BlobUploadResult(
            status="ok",
            detail="uploaded",
            hash=artifact_hash,
            upload=upload_result.model_dump(),
        )

    def download_project_artifact(
        self,
        project_id: str,
        artifact_hash: str,
        *,
        stream: bool | None = None,
        output_path: str | Path | None = None,
    ) -> FileDownloadResponse | Path:
        """Download a project artifact by content hash."""
        spec = self.registry.project_artifacts.download_project_artifact(
            project_id=project_id, artifact_hash=artifact_hash
        )
        return self._download(
            spec,
            options=RequestOptions(stream=stream),
            output_path=output_path,
        )

    # --- Experiment artifacts at step ---

    def upload_and_log_experiment_artifact_at_step(
        self,
        experiment_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        name: str,
        artifact_type: ArtifactType,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
        *,
        verbose: bool = False,
    ) -> LogArtifactAtStepResponse:
        """Upload a file and log step-based artifact metadata in one request."""
        file_spec = FileUploadSpec(
            filename=filename, content=content, content_type=content_type
        )
        factory = self.registry.experiment_artifacts
        spec = factory.upload_and_log_experiment_artifact_at_step(
            experiment_id=experiment_id,
            file=file_spec,
            name=name,
            artifact_type=artifact_type,
            step=step,
            metadata=metadata,
            tags=tags,
        )
        return self._request(spec, options=RequestOptions(verbose=verbose))

    def download_experiment_artifact_at_step(
        self,
        experiment_id: str,
        step: int,
        name: str,
        *,
        stream: bool | None = None,
        output_path: str | Path | None = None,
    ) -> FileDownloadResponse | Path:
        """Download a step-based artifact by ``step`` and logical ``name``."""
        spec = self.registry.experiment_artifacts.download_experiment_artifact_at_step(
            experiment_id=experiment_id, step=step, name=name
        )
        return self._download(
            spec,
            options=RequestOptions(stream=stream),
            output_path=output_path,
        )

    # --- Named / tracked experiment artifacts ---

    def upsert_named_experiment_artifact(
        self,
        experiment_id: str,
        filepath: str,
        filename: str,
        content: bytes,
        content_type: str,
        name: str | None = None,
        *,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """Create or replace a tracked experiment artifact (no training step)."""
        file_spec = FileUploadSpec(
            filename=filename, content=content, content_type=content_type
        )
        spec = self.registry.experiment_artifacts.upsert_named_experiment_artifact(
            experiment_id=experiment_id,
            filepath=filepath,
            file=file_spec,
            name=name,
        )
        result = self.request_client.request(
            spec, options=RequestOptions(verbose=verbose)
        )
        if isinstance(result, BaseModel):
            return result.model_dump()
        return cast(dict[str, Any], result)

    def download_named_experiment_artifact(
        self,
        experiment_id: str,
        filepath: str | None = None,
        blob_id: str | None = None,
        artifact_hash: str | None = None,
        *,
        stream: bool | None = None,
        output_path: str | Path | None = None,
    ) -> FileDownloadResponse | Path:
        """Download a named/tracked artifact by path, blob id, or content hash."""
        spec = self.registry.experiment_artifacts.download_named_experiment_artifact(
            experiment_id=experiment_id,
            filepath=filepath,
            blob_id=blob_id,
            artifact_hash=artifact_hash,
        )
        return self._download(
            spec,
            options=RequestOptions(stream=stream),
            output_path=output_path,
        )
