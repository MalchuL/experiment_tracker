from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from .dto import (
    ArtifactsInfoResultResponse,
    DeleteExperimentArtifactResponse,
    DeleteExperimentArtifactsResponse,
    LogArtifactRequest,
    LogArtifactResponse,
)
from ...request import ApiRequestSpec


class ExperimentArtifactsRequestSpecFactory:
    ENDPOINTS = {
        "get_project_artifacts": lambda project_id: (
            f"/api/experiment-artifacts/projects/{project_id}/get"
        ),
        "upload_and_log_experiment_artifact": lambda experiment_id: (
            f"/api/experiment-artifacts/{experiment_id}/log"
        ),
        "download_experiment_artifact": lambda experiment_id: (
            f"/api/experiment-artifacts/{experiment_id}/download"
        ),
        "delete_experiment_artifact": lambda experiment_id: (
            f"/api/experiment-artifacts/{experiment_id}"
        ),
        "delete_experiment_artifacts": lambda experiment_id: (
            f"/api/experiment-artifacts/experiments/{experiment_id}"
        ),
    }

    def get_project_artifacts(
        self,
        project_id: str | UUID,
        experiment_ids: list[str] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ArtifactsInfoResultResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(str, self.ENDPOINTS["get_project_artifacts"](project_id))

        params: dict[str, object] = {}
        if experiment_ids:
            params["experiment_id"] = experiment_ids
        if artifact_types:
            params["artifact_type"] = artifact_types
        if artifact_names:
            params["artifact_name"] = artifact_names
        if start_time is not None:
            params["start_time"] = start_time.isoformat()
        if end_time is not None:
            params["end_time"] = end_time.isoformat()

        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            query_params=params,
            response_model=ArtifactsInfoResultResponse,
        )

    def upload_and_log_experiment_artifact(
        self,
        experiment_id: str | UUID,
        request: LogArtifactRequest,
    ) -> ApiRequestSpec[LogArtifactResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(
            str, self.ENDPOINTS["upload_and_log_experiment_artifact"](experiment_id)
        )
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=request,
            response_model=LogArtifactResponse,
        )

    def download_experiment_artifact(
        self, experiment_id: str | UUID, path: str
    ) -> ApiRequestSpec[LogArtifactResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["download_experiment_artifact"](experiment_id))
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            query_params={"path": path},
            response_model=LogArtifactResponse,
        )

    def delete_experiment_artifact(
        self, experiment_id: str | UUID, path: str
    ) -> ApiRequestSpec[DeleteExperimentArtifactResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["delete_experiment_artifact"](experiment_id))
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            query_params={"path": path},
            response_model=DeleteExperimentArtifactResponse,
        )

    def delete_experiment_artifacts(
        self, experiment_id: str | UUID
    ) -> ApiRequestSpec[DeleteExperimentArtifactsResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["delete_experiment_artifacts"](experiment_id))
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=DeleteExperimentArtifactsResponse,
        )


ExperimentArtifactsService = ExperimentArtifactsRequestSpecFactory
