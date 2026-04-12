from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from .api import APISchemaFactories
from .request import FileDownloadResponse, FileUploadSpec
from .domain.experiment_artifacts.dto import ArtifactType


class BlobRequestsStrategy:
    """Handles upload and download of binary artifacts through the API.

    Wraps the spec factories for experiment and project artifact endpoints,
    building FileUploadSpec objects and delegating to api.request() for
    uploads and client.download_file() for raw binary downloads.

    Args:
        api: The API facade that owns all spec factories and the HTTP client.
    """

    def __init__(self, api: APISchemaFactories):
        self.api = api

    # -------------------------------------------------------------------------
    # Project artifacts (CAS — content-addressed storage)
    # -------------------------------------------------------------------------

    def check_project_artifacts(
        self, project_id: str, hashes: list[str]
    ) -> dict[str, Any]:
        response = self.api.request(
            self.api.project_artifacts.check_project_artifacts(project_id, hashes)
        )
        if isinstance(response, BaseModel):
            return response.model_dump()
        return cast(dict[str, Any], response)

    def upload_project_artifact(
        self,
        project_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Upload into project CAS if the content hash is not already stored."""
        from experiment_tracker_shared import compute_sha256_hexdigest  # type: ignore

        artifact_hash = compute_sha256_hexdigest(file_content)
        check_result = self.check_project_artifacts(project_id, [artifact_hash])
        missing = set(check_result.get("missing", []))
        if artifact_hash not in missing:
            return {"status": "exists", "hash": artifact_hash}

        file_spec = FileUploadSpec(
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
        )
        spec = self.api.project_artifacts.upload_project_artifact(
            project_id=project_id,
            artifact_hash=artifact_hash,
            file=file_spec,
        )
        upload_result = self.api.request(spec)
        if isinstance(upload_result, BaseModel):
            upload_result = upload_result.model_dump()
        return {"status": "uploaded", "hash": artifact_hash, "upload": upload_result}

    def download_project_artifact(
        self, project_id: str, artifact_hash: str
    ) -> FileDownloadResponse:
        """Download project artifact by content hash, returning content and metadata."""
        spec = self.api.project_artifacts.download_project_artifact(
            project_id=project_id,
            artifact_hash=artifact_hash,
        )
        return cast(FileDownloadResponse, self.api.request(spec))

    def download_project_artifact_to_file(
        self, project_id: str, artifact_hash: str, output_path: str | Path
    ) -> Path:
        """Download project artifact and write it to a local file path."""
        download = self.download_project_artifact(project_id, artifact_hash)
        destination = Path(output_path)
        if destination.is_dir():
            destination = destination / (download.filename or artifact_hash)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(download.content)
        return destination

    # -------------------------------------------------------------------------
    # Experiment artifacts — step-based (logged during training)
    # -------------------------------------------------------------------------

    def upload_and_log_experiment_artifact_at_step(
        self,
        experiment_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Upload file to experiment bucket and log metadata in one call.

        Uses experiment-scoped storage (no deduplication). For deduplicated
        project CAS use upload_project_artifact instead.
        """
        file_spec = FileUploadSpec(
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
        )
        spec = self.api.experiment_artifacts.upload_and_log_experiment_artifact_at_step(
            experiment_id=experiment_id,
            file=file_spec,
            name=name,
            artifact_type=cast(ArtifactType, artifact_type),
            step=step,
            metadata=metadata,
            tags=tags,
        )
        result = self.api.request(spec)
        if isinstance(result, BaseModel):
            return result.model_dump()
        return cast(dict[str, Any], result)

    def download_experiment_artifact_at_step(
        self,
        experiment_id: str,
        step: int,
        name: str,
        artifact_type: str | None = None,
    ) -> FileDownloadResponse:
        """Download artifact for a logged step/name, returning content and metadata."""
        spec = self.api.experiment_artifacts.download_experiment_artifact_at_step(
            experiment_id=experiment_id,
            step=step,
            name=name,
            artifact_type=artifact_type,
        )
        return cast(FileDownloadResponse, self.api.request(spec))

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
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
        )
        spec = self.api.experiment_artifacts.upsert_named_experiment_artifact(
            experiment_id=experiment_id,
            filepath=filepath,
            file=file_spec,
            name=name,
        )
        result = self.api.request(spec)
        if isinstance(result, BaseModel):
            return result.model_dump()
        return cast(dict[str, Any], result)

    # -------------------------------------------------------------------------
    # Backward-compatible wrappers
    # -------------------------------------------------------------------------

    def upload_and_log_experiment_artifact(
        self,
        experiment_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
        name: str,
        artifact_type: str,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.upload_and_log_experiment_artifact_at_step(
            experiment_id=experiment_id,
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
            name=name,
            artifact_type=artifact_type,
            step=step,
            metadata=metadata,
            tags=tags,
        )

    def download_experiment_artifact(
        self,
        experiment_id: str,
        step: int,
        name: str,
        artifact_type: str | None = None,
    ) -> FileDownloadResponse:
        return self.download_experiment_artifact_at_step(
            experiment_id=experiment_id,
            step=step,
            name=name,
            artifact_type=artifact_type,
        )
