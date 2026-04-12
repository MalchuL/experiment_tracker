from __future__ import annotations

import json
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from .dto import (
    ArtifactsAtStepInfoResultResponse,
    ArtifactType,
    ExperimentArtifactResponse,
    DeleteExperimentArtifactAtStepResponse,
    DeleteExperimentArtifactsAtStepResponse,
    LogArtifactAtStepRequest,
    LogArtifactAtStepResponse,
)
from ...request import ApiRequestSpec, FileUploadSpec


class ExperimentArtifactsRequestSpecFactory:
    ENDPOINTS: dict[str, Any] = {
        "get_project_artifacts_at_step": lambda project_id: (
            f"/experiment-artifacts/projects/{project_id}/get-at-step"
        ),
        "upload_and_log_experiment_artifact_at_step": lambda experiment_id: (
            f"/experiment-artifacts/{experiment_id}/log-at-step"
        ),
        "download_experiment_artifact_at_step": lambda experiment_id: (
            f"/experiment-artifacts/{experiment_id}/download-at-step"
        ),
        "delete_experiment_artifact_by_hash": lambda experiment_id: (
            f"/experiment-artifacts/{experiment_id}/at-step"
        ),
        "delete_experiment_all_artifacts": lambda experiment_id: (
            f"/experiment-artifacts/{experiment_id}/all"
        ),
        "upsert_named_experiment_artifact": "/experiment-artifacts/upsert",
        "get_named_experiment_artifact": "/experiment-artifacts/get",
        "download_named_experiment_artifact": "/experiment-artifacts/download",
        "download_named_experiment_artifacts_archive": "/experiment-artifacts/download/archive",
        "delete_named_experiment_artifacts": "/experiment-artifacts/delete",
    }

    def get_project_artifacts_at_step(
        self,
        project_id: str | UUID,
        experiment_ids: list[str] | None = None,
        artifact_types: list[str] | None = None,
        artifact_names: list[str] | None = None,
        steps: list[int] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ArtifactsAtStepInfoResultResponse]:
        if isinstance(project_id, UUID):
            project_id = str(project_id)
        endpoint = cast(
            str, self.ENDPOINTS["get_project_artifacts_at_step"](project_id)
        )

        params: dict[str, object] = {}
        if experiment_ids:
            params["experiment_id"] = experiment_ids
        if artifact_types:
            params["artifact_type"] = artifact_types
        if artifact_names:
            params["artifact_name"] = artifact_names
        if steps:
            params["step"] = steps
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
        file: FileUploadSpec,
        name: str,
        artifact_type: ArtifactType,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> ApiRequestSpec[LogArtifactAtStepResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(
            str,
            self.ENDPOINTS["upload_and_log_experiment_artifact_at_step"](experiment_id),
        )
        form_data: dict[str, str] = {
            "name": name,
            "artifact_type": artifact_type,
            "step": str(step),
        }
        if metadata is not None:
            form_data["metadata"] = json.dumps(metadata)
        if tags is not None:
            form_data["tags"] = json.dumps(tags)
        return ApiRequestSpec(
            method="POST",
            endpoint=endpoint,
            form_data=form_data,
            files={"file": file},
            response_model=LogArtifactAtStepResponse,
        )

    def download_experiment_artifact_at_step(
        self,
        experiment_id: str | UUID,
        step: int,
        name: str,
        artifact_type: str | None = None,
    ) -> ApiRequestSpec:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(
            str, self.ENDPOINTS["download_experiment_artifact_at_step"](experiment_id)
        )
        params: dict[str, object] = {"step": step, "name": name}
        if artifact_type is not None:
            params["artifact_type"] = artifact_type
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            query_params=params,
            response_is_binary=True,
        )

    def delete_experiment_artifact_by_hash(
        self, experiment_id: str | UUID, hash: str
    ) -> ApiRequestSpec[DeleteExperimentArtifactAtStepResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(
            str, self.ENDPOINTS["delete_experiment_artifact_by_hash"](experiment_id)
        )
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            query_params={"hash": hash},
            response_model=DeleteExperimentArtifactAtStepResponse,
        )

    def delete_experiment_all_artifacts(
        self, experiment_id: str | UUID
    ) -> ApiRequestSpec[DeleteExperimentArtifactsAtStepResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        endpoint = cast(
            str, self.ENDPOINTS["delete_experiment_all_artifacts"](experiment_id)
        )
        return ApiRequestSpec(
            method="DELETE",
            endpoint=endpoint,
            response_model=DeleteExperimentArtifactsAtStepResponse,
        )

    def get_named_experiment_artifact(
        self,
        experiment_id: str | UUID,
        filepath: str | None = None,
        blob_id: str | UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ApiRequestSpec[ExperimentArtifactResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        if isinstance(blob_id, UUID):
            blob_id = str(blob_id)
        params: dict[str, str] = {"experiment_id": experiment_id}
        if filepath is not None:
            params["filepath"] = filepath
        if blob_id is not None:
            params["blob_id"] = blob_id
        if artifact_hash is not None:
            params["artifact_hash"] = artifact_hash
        return ApiRequestSpec(
            method="GET",
            endpoint=cast(str, self.ENDPOINTS["get_named_experiment_artifact"]),
            query_params=params,
            response_model=ExperimentArtifactResponse,
        )

    def upsert_named_experiment_artifact(
        self,
        experiment_id: str | UUID,
        filepath: str,
        file: FileUploadSpec,
        name: str | None = None,
    ) -> ApiRequestSpec[ExperimentArtifactResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        form_data: dict[str, str] = {
            "experiment_id": experiment_id,
            "filepath": filepath,
        }
        if name is not None:
            form_data["name"] = name
        return ApiRequestSpec(
            method="POST",
            endpoint=cast(str, self.ENDPOINTS["upsert_named_experiment_artifact"]),
            form_data=form_data,
            files={"file": file},
            response_model=ExperimentArtifactResponse,
        )

    def download_named_experiment_artifact(
        self,
        experiment_id: str | UUID,
        filepath: str | None = None,
        blob_id: str | UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ApiRequestSpec:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        if isinstance(blob_id, UUID):
            blob_id = str(blob_id)
        params: dict[str, str] = {"experiment_id": experiment_id}
        if filepath is not None:
            params["filepath"] = filepath
        if blob_id is not None:
            params["blob_id"] = blob_id
        if artifact_hash is not None:
            params["artifact_hash"] = artifact_hash
        return ApiRequestSpec(
            method="GET",
            endpoint=cast(str, self.ENDPOINTS["download_named_experiment_artifact"]),
            query_params=params,
            response_is_binary=True,
        )

    def download_named_experiment_artifacts_archive(
        self,
        experiment_id: str | UUID,
        name: str,
    ) -> ApiRequestSpec:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        return ApiRequestSpec(
            method="GET",
            endpoint=cast(
                str, self.ENDPOINTS["download_named_experiment_artifacts_archive"]
            ),
            query_params={"experiment_id": experiment_id, "name": name},
            response_is_binary=True,
        )

    def delete_named_experiment_artifacts(
        self,
        experiment_id: str | UUID,
        filepath: str | None = None,
        blob_id: str | UUID | None = None,
        artifact_hash: str | None = None,
    ) -> ApiRequestSpec[DeleteExperimentArtifactsAtStepResponse]:
        if isinstance(experiment_id, UUID):
            experiment_id = str(experiment_id)
        if isinstance(blob_id, UUID):
            blob_id = str(blob_id)
        params: dict[str, str] = {"experiment_id": experiment_id}
        if filepath is not None:
            params["filepath"] = filepath
        if blob_id is not None:
            params["blob_id"] = blob_id
        if artifact_hash is not None:
            params["artifact_hash"] = artifact_hash
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
        steps: list[int] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> ApiRequestSpec[ArtifactsAtStepInfoResultResponse]:
        return self.get_project_artifacts_at_step(
            project_id=project_id,
            experiment_ids=experiment_ids,
            artifact_types=artifact_types,
            artifact_names=artifact_names,
            steps=steps,
            start_time=start_time,
            end_time=end_time,
        )

    def upload_and_log_experiment_artifact(
        self,
        experiment_id: str | UUID,
        file: FileUploadSpec,
        name: str,
        artifact_type: ArtifactType,
        step: int,
        metadata: dict[str, str] | None = None,
        tags: list[str] | None = None,
    ) -> ApiRequestSpec[LogArtifactAtStepResponse]:
        return self.upload_and_log_experiment_artifact_at_step(
            experiment_id=experiment_id,
            file=file,
            name=name,
            artifact_type=artifact_type,
            step=step,
            metadata=metadata,
            tags=tags,
        )

    def delete_experiment_artifact(
        self, experiment_id: str | UUID, hash: str
    ) -> ApiRequestSpec[DeleteExperimentArtifactAtStepResponse]:
        return self.delete_experiment_artifact_by_hash(
            experiment_id=experiment_id,
            hash=hash,
        )

    def download_experiment_artifact(
        self,
        experiment_id: str | UUID,
        step: int,
        name: str,
        artifact_type: str | None = None,
    ) -> ApiRequestSpec:
        return self.download_experiment_artifact_at_step(
            experiment_id=experiment_id,
            step=step,
            name=name,
            artifact_type=artifact_type,
        )

    def delete_experiment_artifacts_at_step(
        self, experiment_id: str | UUID
    ) -> ApiRequestSpec[DeleteExperimentArtifactsAtStepResponse]:
        return self.delete_experiment_all_artifacts(experiment_id=experiment_id)


ExperimentArtifactsService = ExperimentArtifactsRequestSpecFactory
