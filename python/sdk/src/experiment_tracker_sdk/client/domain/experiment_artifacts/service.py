from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from .dto import (
    ArtifactsAtStepInfoResultResponse,
    ExperimentArtifactResponse,
    DeleteExperimentArtifactAtStepResponse,
    DeleteExperimentArtifactsAtStepResponse,
    LogArtifactAtStepRequest,
    LogArtifactAtStepResponse,
)
from ...request import ApiRequestSpec


class ExperimentArtifactsRequestSpecFactory:
    ENDPOINTS = {
        "get_project_artifacts_at_step": lambda project_id: (
            f"/api/experiment-artifacts/projects/{project_id}/get-at-step"
        ),
        "upload_and_log_experiment_artifact_at_step": lambda experiment_id: (
            f"/api/experiment-artifacts/{experiment_id}/log-at-step"
        ),
        "download_experiment_artifact_at_step": lambda experiment_id: (
            f"/api/experiment-artifacts/{experiment_id}/download-at-step"
        ),
        "delete_experiment_artifact_at_step": lambda experiment_id: (
            f"/api/experiment-artifacts/{experiment_id}/at-step"
        ),
        "delete_experiment_artifacts_at_step": lambda experiment_id: (
            f"/api/experiment-artifacts/{experiment_id}/at-step"
        ),
        "upsert_named_experiment_artifact": "/api/experiment-artifacts/upsert",
        "get_named_experiment_artifact": "/api/experiment-artifacts/get",
        "download_named_experiment_artifact": "/api/experiment-artifacts/download",
        "download_named_experiment_artifacts_archive": "/api/experiment-artifacts/download/archive",
        "delete_named_experiment_artifacts": "/api/experiment-artifacts/delete",
    }

    def get_project_artifacts_at_step(
        self,
        project_id: str | UUID,
        experiment_ids: list[str] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ArtifactsAtStepInfoResultResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(str, self.ENDPOINTS["get_project_artifacts_at_step"](project_id))

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
            response_model=ArtifactsAtStepInfoResultResponse,
        )

    def upload_and_log_experiment_artifact_at_step(
        self,
        experiment_id: str | UUID,
        request: LogArtifactAtStepRequest,
    ) -> ApiRequestSpec[LogArtifactAtStepResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(
            str, self.ENDPOINTS["upload_and_log_experiment_artifact_at_step"](experiment_id)
        )
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            request_payload=request,
            response_model=LogArtifactAtStepResponse,
        )

    def download_experiment_artifact_at_step(
        self, experiment_id: str | UUID, path: str
    ) -> ApiRequestSpec[LogArtifactAtStepResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["download_experiment_artifact_at_step"](experiment_id))
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            query_params={"path": path},
            response_model=LogArtifactAtStepResponse,
        )

    def delete_experiment_artifact_at_step(
        self, experiment_id: str | UUID, path: str
    ) -> ApiRequestSpec[DeleteExperimentArtifactAtStepResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["delete_experiment_artifact_at_step"](experiment_id))
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            query_params={"path": path},
            response_model=DeleteExperimentArtifactAtStepResponse,
        )

    def delete_experiment_artifacts_at_step(
        self, experiment_id: str | UUID
    ) -> ApiRequestSpec[DeleteExperimentArtifactsAtStepResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(str, self.ENDPOINTS["delete_experiment_artifacts_at_step"](experiment_id))
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=DeleteExperimentArtifactsAtStepResponse,
        )

    def get_named_experiment_artifact(
        self,
        experiment_id: str | UUID,
        name: str,
        filepath: str,
    ) -> ApiRequestSpec[ExperimentArtifactResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        return ApiRequestSpec(
            method="GET",
            endpoint=cast(str, self.ENDPOINTS["get_named_experiment_artifact"]),
            query_params={
                "experiment_id": experiment_id,
                "name": name,
                "filepath": filepath,
            },
            response_model=ExperimentArtifactResponse,
        )

    def download_named_experiment_artifact(
        self,
        experiment_id: str | UUID,
        name: str,
        filepath: str,
    ) -> ApiRequestSpec[ExperimentArtifactResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        return ApiRequestSpec(
            method="GET",
            endpoint=cast(str, self.ENDPOINTS["download_named_experiment_artifact"]),
            query_params={
                "experiment_id": experiment_id,
                "name": name,
                "filepath": filepath,
            },
            response_model=ExperimentArtifactResponse,
        )

    def download_named_experiment_artifacts_archive(
        self,
        experiment_id: str | UUID,
        name: str,
    ) -> ApiRequestSpec[ExperimentArtifactResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        return ApiRequestSpec(
            method="GET",
            endpoint=cast(str, self.ENDPOINTS["download_named_experiment_artifacts_archive"]),
            query_params={"experiment_id": experiment_id, "name": name},
            response_model=ExperimentArtifactResponse,
        )

    def delete_named_experiment_artifacts(
        self,
        experiment_id: str | UUID,
        name: str,
        filepath: str | None = None,
    ) -> ApiRequestSpec[DeleteExperimentArtifactsAtStepResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        params: dict[str, str] = {
            "experiment_id": experiment_id,
            "name": name,
        }
        if filepath is not None:
            params["filepath"] = filepath
        return ApiRequestSpec(
            method="DELETE",
            endpoint=cast(str, self.ENDPOINTS["delete_named_experiment_artifacts"]),
            query_params=params,
            response_model=DeleteExperimentArtifactsAtStepResponse,
        )

    # Backward-compatible aliases for step-based flow.
    def get_project_artifacts(
        self,
        project_id: str | UUID,
        experiment_ids: list[str] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ArtifactsAtStepInfoResultResponse]:
        return self.get_project_artifacts_at_step(
            project_id=project_id,
            experiment_ids=experiment_ids,
            artifact_types=artifact_types,
            artifact_names=artifact_names,
            start_time=start_time,
            end_time=end_time,
        )

    def upload_and_log_experiment_artifact(
        self,
        experiment_id: str | UUID,
        request: LogArtifactAtStepRequest,
    ) -> ApiRequestSpec[LogArtifactAtStepResponse]:
        return self.upload_and_log_experiment_artifact_at_step(
            experiment_id=experiment_id,
            request=request,
        )

    def delete_experiment_artifact(
        self, experiment_id: str | UUID, path: str
    ) -> ApiRequestSpec[DeleteExperimentArtifactAtStepResponse]:
        return self.delete_experiment_artifact_at_step(
            experiment_id=experiment_id,
            path=path,
        )

    def download_experiment_artifact(
        self, experiment_id: str | UUID, path: str
    ) -> ApiRequestSpec[LogArtifactAtStepResponse]:
        return self.download_experiment_artifact_at_step(
            experiment_id=experiment_id,
            path=path,
        )

    def delete_experiment_artifacts(
        self, experiment_id: str | UUID
    ) -> ApiRequestSpec[DeleteExperimentArtifactsAtStepResponse]:
        return self.delete_experiment_artifacts_at_step(experiment_id=experiment_id)


ExperimentArtifactsService = ExperimentArtifactsRequestSpecFactory
