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
        """Check which project artifact hashes are absent from project storage.

        Args:
            project_id: Project namespace used for the content-addressed artifact
                lookup.
            hashes: SHA-256 content hashes to test before deciding whether any
                matching blobs need to be uploaded.

        Returns:
            Response describing which requested hashes are already present and
            which are missing from the project artifact store.
        """
        response: CheckProjectArtifactsResponse = self.request_client.request(
            self.registry.project_artifacts.check_project_artifacts(project_id, hashes)  # type: ignore[assignment]
        )
        return response

    def upload_project_artifact(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> BlobUploadResult:
        """Upload bytes into project content-addressed storage when needed.

        Computes the SHA-256 hash of ``content`` and checks whether that hash is
        already present for the project. If the blob exists, no upload request is
        sent. If it is missing, the bytes are uploaded with the caller-provided
        upload metadata.

        Args:
            project_id: Project namespace where the content-addressed artifact
                should be available.
            filename: Name to send in the multipart upload metadata, used by
                downstream services for artifact records and download hints.
            content: Raw artifact bytes whose hash determines the storage key.
            content_type: MIME type describing the uploaded bytes for storage
                metadata and later download responses.

        Returns:
            Upload summary containing the computed hash, whether the blob already
            existed or was uploaded, and the underlying upload response when an
            upload was performed.
        """
        from experiment_tracker_shared import compute_sha256_hexdigest  # type: ignore

        artifact_hash = compute_sha256_hexdigest(content)
        check_result = self.check_project_artifacts(project_id, [artifact_hash])
        missing = set(check_result.missing)
        if artifact_hash not in missing:
            return BlobUploadResult(
                status="ok", detail="exists", hash=artifact_hash, upload={}
            )

        file_spec = FileUploadSpec(
            filename=filename,
            content=content,
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
        """Download a project artifact by its content hash.

        Args:
            project_id: Project namespace to read the content-addressed artifact
                from.
            artifact_hash: SHA-256 hash identifying the stored blob.
            as_stream_download: Optional request-client flag controlling whether
                the underlying HTTP response should be handled as a streamed file
                download.

        Returns:
            Download response containing the artifact bytes and response-derived
            metadata such as filename and content type.
        """
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
        """Download a project artifact and persist it to the local filesystem.

        Args:
            project_id: Project namespace to read the content-addressed artifact
                from.
            artifact_hash: SHA-256 hash identifying the stored blob.
            output_path: Destination file path or directory. When a directory is
                provided, the download helper uses the filename from the response
                metadata.

        Returns:
            Final path where the downloaded bytes were written.
        """
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
        content: bytes,
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

        Args:
            experiment_id: Experiment that owns the step-based artifact.
            filename: Name to send in the multipart upload metadata, used as the
                stored file's download hint.
            content: Raw artifact bytes to upload for this training step.
            content_type: MIME type describing the uploaded bytes.
            name: Logical artifact name used with ``step`` to query or download
                this logged artifact later.
            artifact_type: Artifact category stored with the scalar artifact
                metadata for filtering and display.
            step: Training step associated with this artifact record.
            metadata: Optional string metadata stored with the artifact info row.
            tags: Optional labels stored with the artifact info row for later
                filtering or organization.

        Returns:
            Response from the experiment artifact log endpoint, including the
            stored artifact metadata returned by the API.
        """
        file_spec = FileUploadSpec(
            filename=filename,
            content=content,
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
        """Download a step-based experiment artifact.

        Args:
            experiment_id: Experiment that owns the logged artifact.
            step: Training step used to identify the artifact record.
            name: Logical artifact name used with ``step`` to select the stored
                artifact.
            as_stream_download: Optional request-client flag controlling whether
                the underlying HTTP response should be handled as a streamed file
                download.

        Returns:
            Download response containing the artifact bytes and response-derived
            metadata such as filename and content type.
        """
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
        """Download a step-based experiment artifact to a local file.

        Args:
            experiment_id: Experiment that owns the logged artifact.
            step: Training step used to identify the artifact record.
            name: Logical artifact name used with ``step`` to select the stored
                artifact.
            output_path: Destination file path or directory. When a directory is
                provided, the download helper uses the filename from the response
                metadata.

        Returns:
            Final path where the downloaded bytes were written.
        """
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
        filename: str,
        content: bytes,
        content_type: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create or replace a tracked experiment artifact that is not step-based.

        Args:
            experiment_id: Experiment that owns the tracked artifact.
            filepath: Stable artifact path within the experiment's tracked
                artifact namespace; repeated uploads to the same path update the
                stored artifact record.
            filename: Name to send in the multipart upload metadata, used by the
                storage service and as a download hint.
            content: Raw artifact bytes to store for the tracked artifact.
            content_type: MIME type describing the uploaded bytes.
            name: Optional display or logical name stored with the tracked
                artifact record in addition to ``filepath``.

        Returns:
            Artifact record returned by the API as a dictionary.
        """
        file_spec = FileUploadSpec(
            filename=filename,
            content=content,
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
        """Download a tracked experiment artifact that is not step-based.

        Args:
            experiment_id: Experiment that owns the tracked artifact.
            filepath: Optional tracked artifact path to resolve. Provide one of
                ``filepath``, ``blob_id``, or ``artifact_hash`` according to the
                API lookup mode you want to use.
            blob_id: Optional storage record identifier used to resolve the
                artifact without relying on its path.
            artifact_hash: Optional content hash used to resolve the artifact by
                stored bytes.
            as_stream_download: Optional request-client flag controlling whether
                the underlying HTTP response should be handled as a streamed file
                download.

        Returns:
            Download response containing the artifact bytes and response-derived
            metadata such as filename and content type.
        """
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
        """Download a tracked experiment artifact to a local file.

        Args:
            experiment_id: Experiment that owns the tracked artifact.
            output_path: Destination file path or directory. When a directory is
                provided, the download helper uses the filename from the response
                metadata.
            filepath: Optional tracked artifact path to resolve. Provide one of
                ``filepath``, ``blob_id``, or ``artifact_hash`` according to the
                API lookup mode you want to use.
            blob_id: Optional storage record identifier used to resolve the
                artifact without relying on its path.
            artifact_hash: Optional content hash used to resolve the artifact by
                stored bytes.

        Returns:
            Final path where the downloaded bytes were written.
        """
        download: FileDownloadResponse = self.download_named_experiment_artifact(
            experiment_id=experiment_id,
            filepath=filepath,
            blob_id=blob_id,
            artifact_hash=artifact_hash,
        )
        return dump_binary_content_to_path(
            download.content, output_path, download.filename
        )
