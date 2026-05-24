import pytest
from pydantic import ValidationError

from experiment_tracker_sdk.client.domain import (
    ExperimentRequestSpecFactory,
    MetricRequestSpecFactory,
    ProjectArtifactsRequestSpecFactory,
    TeamRequestSpecFactory,
)
from experiment_tracker_sdk.client.domain.teams.dto import TeamCreateRequest, TeamUpdateRequest
from experiment_tracker_sdk.client.request import ApiRequestSpec, FileUploadSpec
from experiment_tracker_sdk.client.domain.project_artifacts.dto import UploadProjectArtifactResponse
from experiment_tracker_sdk.config import compose_base_url, normalize_api_prefix


def test_api_request_spec_rejects_json_and_form_mix() -> None:
    try:
        ApiRequestSpec(
            method="POST",
            endpoint="/metrics",
            request_payload={"name": "acc"},
            form_data={"name": "acc"},
        )
    except ValueError as exc:
        assert "cannot contain both request_payload" in str(exc)
        return
    raise AssertionError("Expected ValueError for mixed json and form payload")


def test_api_request_spec_accepts_files_without_json() -> None:
    spec = ApiRequestSpec(
        method="POST",
        endpoint="/experiment-artifacts/upsert",
        form_data={"name": "artifact"},
        files={
            "file": FileUploadSpec(
                filename="artifact.bin",
                content=b"abc",
            )
        },
    )
    assert spec.files is not None


def test_compose_base_url_applies_prefix_once() -> None:
    assert compose_base_url("http://127.0.0.1:8000", "/api") == "http://127.0.0.1:8000/api"
    assert compose_base_url("http://127.0.0.1:8000/api", "/api") == "http://127.0.0.1:8000/api"
    assert compose_base_url("http://127.0.0.1:8000", "") == "http://127.0.0.1:8000"


def test_normalize_api_prefix() -> None:
    assert normalize_api_prefix(None) == "/api"
    assert normalize_api_prefix("api") == "/api"
    assert normalize_api_prefix("/api/") == "/api"
    assert normalize_api_prefix("") == ""


def test_team_create_request_rejects_owner_id() -> None:
    with pytest.raises(ValidationError):
        TeamCreateRequest.model_validate({"name": "Team", "ownerId": "other-user"})


def test_team_update_request_rejects_owner_id() -> None:
    with pytest.raises(ValidationError):
        TeamUpdateRequest.model_validate(
            {"id": "team-1", "name": "Team", "ownerId": "other-user"}
        )


def test_endpoint_factories_are_prefixless() -> None:
    experiment_factory = ExperimentRequestSpecFactory()
    metrics_factory = MetricRequestSpecFactory()
    project_artifacts_factory = ProjectArtifactsRequestSpecFactory()
    team_factory = TeamRequestSpecFactory()

    assert experiment_factory.create_experiment("project-id", "run").endpoint == "/experiments"
    assert metrics_factory.upsert_metric("exp-id", "acc", 0.5).endpoint == "/metrics"
    dummy_file = FileUploadSpec(filename="data.bin", content=b"x")
    assert (
        project_artifacts_factory.upload_project_artifact(
            "project-id", "abc123", dummy_file
        ).endpoint
        == "/project-artifacts/project-id/upload"
    )
    assert team_factory.get_all_teams().endpoint == "/teams"
    assert team_factory.get_team("team-id").endpoint == "/teams/team-id"
    assert metrics_factory.get_metric("exp-id", "acc").endpoint == "/metrics/by-key"


def test_create_experiment_spec_serializes_feature_tree() -> None:
    experiment_factory = ExperimentRequestSpecFactory()
    spec = experiment_factory.create_experiment(
        "project-id",
        "run",
        features=[
            {
                "name": "training",
                "children": [{"name": "optimizer-adam"}],
            }
        ],
    )

    assert spec.request_payload is not None
    payload = spec.request_payload.model_dump()
    assert payload["features"] == [
        {
            "name": "training",
            "children": [{"name": "optimizer-adam", "children": None}],
        }
    ]
