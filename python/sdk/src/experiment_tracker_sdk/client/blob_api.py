from io import BytesIO
from pathlib import Path
from typing import Any, Literal, cast

from experiment_tracker_sdk.client.domain.project_artifacts.dto import (
    CheckProjectArtifactsResponse,
    UploadProjectArtifactResponse,
)
from experiment_tracker_sdk.client.utils.downloading import dump_binary_content_to_path
from pydantic import BaseModel, Field

from .api_registry import APIRequestsRegistry
from .request_types import FileDownloadResponse, FileUploadSpec
from .domain.experiment_artifacts.dto import ArtifactType, LogArtifactAtStepResponse
from .client import ExperimentTrackerClient


class BlobUploadResult(BaseModel):
    """Result of a blob upload."""

    status: Literal["ok", "error"] = Field(description="Status of the upload.")
    detail: Literal["exists", "uploaded", "error"] = Field(
        description="Detail of the upload."
    )
    hash: str = Field(description="Hash of the uploaded blob.")
    upload: dict[str, Any] = Field(description="Upload result.")


class BlobRequestsStrategy:
    """Handles upload and download of binary artifacts through the API.

    Wraps the spec factories for experiment and project artifact endpoints,
    building FileUploadSpec objects and delegating to api.request() for
    uploads and client.download_file() for raw binary downloads.

    Args:
        registry: The API requests registry.
        request_client: The HTTP client.
    """

    def __init__(
        self, registry: APIRequestsRegistry, request_client: ExperimentTrackerClient
    ):
        self.registry = registry
        self.request_client = request_client

    # -------------------------------------------------------------------------
    # Project artifacts (CAS — content-addressed storage)
    # -------------------------------------------------------------------------

    def check_project_artifacts(
        self, project_id: str, hashes: list[str]
    ) -> CheckProjectArtifactsResponse:
        response: CheckProjectArtifactsResponse = self.request_client.request(
            self.registry.project_artifacts.check_project_artifacts(project_id, hashes)  # type: ignore[assignment]
        )
        return response

    def upload_project_artifact(
        self,
        project_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
    ) -> BlobUploadResult:
        """Upload into project CAS if the content hash is not already stored."""
        from experiment_tracker_shared import compute_sha256_hexdigest  # type: ignore

        artifact_hash = compute_sha256_hexdigest(file_content)
        check_result = self.check_project_artifacts(project_id, [artifact_hash])
        missing = set(check_result.missing)
        if artifact_hash not in missing:
            return BlobUploadResult(
                status="ok", detail="exists", hash=artifact_hash, upload={}
            )

        file_spec = FileUploadSpec(
            filename=file_name,
            content=file_content,
            content_type=content_type,
        )
        spec = self.registry.project_artifacts.upload_project_artifact(
            project_id=project_id,
            artifact_hash=artifact_hash,
            file=file_spec,
        )
        upload_result: UploadProjectArtifactResponse = self.request_client.request(spec)  # type: ignore[assignment]
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
        as_stream_download: bool | None = None,
    ) -> FileDownloadResponse:
        """Download project artifact by content hash, returning content and metadata."""
        spec = self.registry.project_artifacts.download_project_artifact(
            project_id=project_id,
            artifact_hash=artifact_hash,
        )
        return cast(
            FileDownloadResponse,
            self.request_client.request(spec, as_stream_download=as_stream_download),
        )

    def download_project_artifact_to_file(
        self, project_id: str, artifact_hash: str, output_path: str | Path
    ) -> Path:
        """Download project artifact and write it to a local file path."""
        download: FileDownloadResponse = self.download_project_artifact(
            project_id, artifact_hash
        )
        destination = dump_binary_content_to_path(
            download.content, output_path, download.filename
        )
        return destination

    # -------------------------------------------------------------------------
    # Experiment artifacts — step-based (logged during training)
    # -------------------------------------------------------------------------

    def upload_and_log_experiment_artifact_at_step(
        self,
        experiment_id: str,
        filename: str,
        file_content: bytes,
        content_type: str,
        name: str,
        artifact_type: ArtifactType,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> LogArtifactAtStepResponse:
        """Upload file to experiment bucket and log metadata in one call.

        Uses experiment-scoped storage (no deduplication). For deduplicated
        project CAS use upload_project_artifact instead.
        """
        file_spec = FileUploadSpec(
            filename=filename,
            content=file_content,
            content_type=content_type,
        )
        spec = self.registry.experiment_artifacts.upload_and_log_experiment_artifact_at_step(
            experiment_id=experiment_id,
            file=file_spec,
            name=name,
            artifact_type=artifact_type,
            step=step,
            metadata=metadata,
            tags=tags,
        )
        result: LogArtifactAtStepResponse = self.request_client.request(spec)  # type: ignore[assignment]
        return result

    def download_experiment_artifact_at_step(
        self,
        experiment_id: str,
        step: int,
        name: str,
        as_stream_download: bool | None = None,
    ) -> FileDownloadResponse:
        """Download artifact for a logged step/name, returning content and metadata."""
        spec = self.registry.experiment_artifacts.download_experiment_artifact_at_step(
            experiment_id=experiment_id, step=step, name=name
        )
        return cast(
            FileDownloadResponse,
            self.request_client.request(spec, as_stream_download=as_stream_download),
        )

    def download_experiment_artifact_at_step_to_file(
        self, experiment_id: str, step: int, name: str, output_path: str | Path
    ) -> Path:
        """Download artifact for a logged step/name and write it to a local file path."""
        download: FileDownloadResponse = self.download_experiment_artifact_at_step(
            experiment_id=experiment_id,
            step=step,
            name=name,
        )
        return dump_binary_content_to_path(
            download.content, output_path, download.filename
        )

    # -------------------------------------------------------------------------
    # Experiment artifacts — named / tracked (no step)
    # -------------------------------------------------------------------------

    def upsert_named_experiment_artifact(
        self,
        experiment_id: str,
        filepath: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Upsert a named tracked artifact for an experiment (no step)."""
        file_spec = FileUploadSpec(
            filename=file_name,
            content=file_content,
            content_type=content_type,
        )
        spec = self.registry.experiment_artifacts.upsert_named_experiment_artifact(
            experiment_id=experiment_id,
            filepath=filepath,
            file=file_spec,
            name=name,
        )
        result = self.request_client.request(spec)
        if isinstance(result, BaseModel):
            return result.model_dump()
        return cast(dict[str, Any], result)

    def download_named_experiment_artifact(
        self,
        experiment_id: str,
        filepath: str | None = None,
        blob_id: str | None = None,
        artifact_hash: str | None = None,
        as_stream_download: bool | None = None,
    ) -> FileDownloadResponse:
        """Download a named tracked artifact for an experiment (no step)."""
        spec = self.registry.experiment_artifacts.download_named_experiment_artifact(
            experiment_id=experiment_id,
            filepath=filepath,
            blob_id=blob_id,
            artifact_hash=artifact_hash,
        )
        return cast(
            FileDownloadResponse,
            self.request_client.request(spec, as_stream_download=as_stream_download),
        )

    def download_named_experiment_artifact_to_file(
        self,
        experiment_id: str,
        output_path: str | Path,
        filepath: str | None = None,
        blob_id: str | None = None,
        artifact_hash: str | None = None,
    ) -> Path:
        """Download a named tracked artifact for an experiment (no step) and write it to a local file path."""
        download: FileDownloadResponse = self.download_named_experiment_artifact(
            experiment_id=experiment_id,
            filepath=filepath,
            blob_id=blob_id,
            artifact_hash=artifact_hash,
        )
        return dump_binary_content_to_path(
            download.content, output_path, download.filename
        )
