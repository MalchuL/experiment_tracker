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

    def check_blobs(self, hashes: list[str]) -> dict[str, Any]:
        return self._client.request_json("POST", "/api/blobs/check", json=hashes)

    def upload_blob(
        self,
        blob_hash: str,
        file_name: str,
        file_content: bytes,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        return self._client.upload_file(
            "/api/blobs/upload",
            params={"hash": blob_hash},
            file_name=file_name,
            file_content=file_content,
            content_type=content_type,
        )

    def download_blob(self, blob_hash: str) -> bytes:
        """Download blob bytes by object-storage hash/reference."""
        return self._client.download_file(f"/api/blobs/{blob_hash}")

    def download_blob_to_file(
        self, blob_hash: str, output_path: str | Path
    ) -> Path:
        """Download blob and write it to a local file path."""
        return self._client.download_file_to_path(
            f"/api/blobs/{blob_hash}",
            output_path=output_path,
        )
