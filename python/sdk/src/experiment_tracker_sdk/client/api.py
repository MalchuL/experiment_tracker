from experiment_tracker_sdk.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.request import ApiRequestSpec
from experiment_tracker_sdk.client.domain import (
    ExperimentRequestSpecFactory,
    MetricRequestSpecFactory,
    ProjectRequestSpecFactory,
    ScalarsRequestSpecFactory,
    HypothesisRequestSpecFactory,
    ObjectsRequestSpecFactory,
    TeamRequestSpecFactory,
)
from pydantic import BaseModel
from typing import Any, TypeVar
from pathlib import Path

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class API:
    def __init__(self, client: ExperimentTrackerClient):
        self._client = client
        self._experiment_service = ExperimentRequestSpecFactory()
        self._metric_service = MetricRequestSpecFactory()
        self._project_service = ProjectRequestSpecFactory()
        self._scalars_service = ScalarsRequestSpecFactory()
        self._hypothesis_service = HypothesisRequestSpecFactory()
        self._team_service = TeamRequestSpecFactory()
        self._objects_service = ObjectsRequestSpecFactory()

    @property
    def experiments(self) -> ExperimentRequestSpecFactory:
        return self._experiment_service

    @property
    def metrics(self) -> MetricRequestSpecFactory:
        return self._metric_service

    @property
    def projects(self) -> ProjectRequestSpecFactory:
        return self._project_service

    @property
    def scalars(self) -> ScalarsRequestSpecFactory:
        return self._scalars_service

    @property
    def hypotheses(self) -> HypothesisRequestSpecFactory:
        return self._hypothesis_service

    @property
    def teams(self) -> TeamRequestSpecFactory:
        return self._team_service

    @property
    def objects(self) -> ObjectsRequestSpecFactory:
        return self._objects_service

    def request(
        self, request_spec: ApiRequestSpec[ResponseT]
    ) -> ResponseT | list[ResponseT] | dict[str, Any]:
        return self._client.request(request_spec)

    def queued_request(self, request_spec: ApiRequestSpec[Any]) -> None:
        self._client.queued_request(request_spec)

    def flush(self) -> None:
        """Flush the request queue."""
        self._client.flush()

    def close(self) -> None:
        """Close the request queue and underlying HTTP client."""
        self._client.close()

    def check_project_artifacts(
        self, project_id: str, hashes: list[str]
    ) -> dict[str, Any]:
        return self._client.request_json(
            method="POST",
            path=f"/api/project-artifacts/{project_id}/check",
            json=hashes,
        )

    def upload_project_artifact(
        self,
        project_id: str,
        file_name: str,
        file_content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Upload into project CAS if hash is missing."""

        from experiment_tracker_shared import compute_sha256_hexdigest

        artifact_hash = compute_sha256_hexdigest(file_content)
        check_result = self.check_project_artifacts(project_id, [artifact_hash])
        missing = set(check_result.get("missing", []))
        if artifact_hash not in missing:
            return {"status": "exists", "hash": artifact_hash}
        upload_result = self._client.upload_file(
            path=f"/api/project-artifacts/{project_id}/upload",
            params={"hash": artifact_hash},
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
        )
        return {"status": "uploaded", "hash": artifact_hash, "upload": upload_result}

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
        """Upload file to experiment bucket and log metadata in one call.

        Uses experiment-scoped storage (no deduplication). For deduplicated
        project CAS, use upload_and_log_artifact instead.
        """
        import json

        form_data: dict[str, Any] = {
            "name": name,
            "artifact_type": artifact_type,
            "step": str(step),
        }
        if metadata:
            form_data["metadata"] = json.dumps(metadata)
        if tags:
            form_data["tags"] = json.dumps(tags)
        return self._client.upload_artifact(
            path=f"/api/experiment-artifacts/{experiment_id}/log",
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
            form_data=form_data,
        )

    def download_project_artifact(self, project_id: str, artifact_hash: str) -> bytes:
        """Download project artifact bytes by hash (project-scoped CAS)."""
        return self._client.download_file(
            f"/api/project-artifacts/{project_id}/artifacts/{artifact_hash}"
        )

    def download_experiment_artifact(self, experiment_id: str, path: str) -> bytes:
        """Download artifact by path from experiment bucket."""
        return self._client.download_file(
            f"/api/experiment-artifacts/{experiment_id}/download",
            params={"path": path},
        )

    def download_project_artifact_to_file(
        self, project_id: str, artifact_hash: str, output_path: str | Path
    ) -> Path:
        """Download project artifact and write it to a local file path."""
        return self._client.download_file_to_path(
            f"/api/project-artifacts/{project_id}/artifacts/{artifact_hash}",
            output_path=output_path,
        )
