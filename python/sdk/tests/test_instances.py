from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import pytest
from pydantic import BaseModel

from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.domain.experiments.dto import (
    ExperimentResponse,
    ExperimentStatus,
)
from experiment_tracker_sdk.client.domain.metrics.dto import MetricResponse
from experiment_tracker_sdk.client.domain.projects.dto import (
    ProjectMetricsResponse,
    ProjectOwnerResponse,
    ProjectResponse,
)
from experiment_tracker_sdk.client.domain.teams.dto import TeamResponse
from experiment_tracker_sdk.client.instances import (
    ExperimentInstance,
    MetricInstance,
    ProjectInstance,
    TeamInstance,
)
from experiment_tracker_sdk.client.request_types import ApiRequestSpec
from experiment_tracker_sdk.error import ExpTrackerAPIError

PROJECT_ID = "11111111-1111-4111-8111-111111111111"
TEAM_ID = "22222222-2222-4222-8222-222222222222"
EXPERIMENT_ID = "33333333-3333-4333-8333-333333333333"
METRIC_ID = "44444444-4444-4444-8444-444444444444"
USER_ID = "55555555-5555-4555-8555-555555555555"


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[ApiRequestSpec[Any]] = []

    def request(self, spec: ApiRequestSpec[Any]) -> Any:
        self.calls.append(spec)
        payload = _payload_dict(spec.request_payload)
        if spec.endpoint == "/projects" and spec.method == "POST":
            return _project(PROJECT_ID, payload.get("name", "project"))
        if spec.endpoint == f"/projects/{PROJECT_ID}" and spec.method == "GET":
            return _project(PROJECT_ID, "project")
        if spec.endpoint == f"/projects/{PROJECT_ID}" and spec.method == "PATCH":
            return _project(PROJECT_ID, payload.get("name", "project"))
        if spec.endpoint == f"/projects/{PROJECT_ID}" and spec.method == "DELETE":
            return {"success": True}
        if spec.endpoint == "/teams" and spec.method == "POST":
            return _team(TEAM_ID, payload.get("name", "team"))
        if spec.endpoint == f"/teams/{TEAM_ID}" and spec.method == "GET":
            return _team(TEAM_ID, "team")
        if spec.endpoint == "/teams" and spec.method == "PATCH":
            return _team(payload.get("id", TEAM_ID), payload.get("name", "team"))
        if spec.endpoint == f"/teams/{TEAM_ID}" and spec.method == "DELETE":
            return {"success": True}
        if spec.endpoint == "/experiments" and spec.method == "POST":
            return _experiment(EXPERIMENT_ID, payload.get("name", "experiment"))
        if spec.endpoint == f"/experiments/{EXPERIMENT_ID}" and spec.method == "GET":
            return _experiment(EXPERIMENT_ID, "experiment")
        if spec.endpoint == f"/experiments/{EXPERIMENT_ID}" and spec.method == "PATCH":
            return _experiment(
                EXPERIMENT_ID,
                payload.get("name", "experiment"),
                status=payload.get("status", "planned"),
            )
        if spec.endpoint == f"/experiments/{EXPERIMENT_ID}" and spec.method == "DELETE":
            return {"success": True}
        if spec.endpoint == "/metrics" and spec.method == "POST":
            return _metric(
                METRIC_ID,
                payload.get("experimentId", EXPERIMENT_ID),
                payload.get("name", "metric"),
                payload.get("value", 0.0),
                payload.get("label"),
            )
        if spec.endpoint == "/metrics/by-key" and spec.method == "GET":
            assert spec.query_params is not None
            return _metric(
                METRIC_ID,
                spec.query_params["experimentId"],
                spec.query_params["name"],
                0.5,
                spec.query_params.get("label"),
            )
        if spec.endpoint == f"/metrics/{METRIC_ID}" and spec.method == "DELETE":
            return None
        raise AssertionError(f"Unexpected request: {spec.method} {spec.endpoint}")

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


def _payload_dict(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, BaseModel):
        return payload.model_dump(exclude_unset=True)
    return dict(payload)


def _project(project_id: str, name: str) -> ProjectResponse:
    return ProjectResponse(
        id=project_id,
        name=name,
        description="",
        metrics=ProjectMetricsResponse(),
        settings=[],
        owner=ProjectOwnerResponse(id=USER_ID),
        createdAt=datetime(2026, 1, 1),
    )


def _team(team_id: str, name: str) -> TeamResponse:
    return TeamResponse(
        id=team_id,
        createdAt=datetime(2026, 1, 1),
        ownerId=USER_ID,
        name=name,
        description=None,
    )


def _experiment(
    experiment_id: str,
    name: str,
    *,
    status: str = "planned",
) -> ExperimentResponse:
    return ExperimentResponse(
        id=experiment_id,
        projectId=PROJECT_ID,
        name=name,
        description="",
        status=status,
        createdAt=datetime(2026, 1, 1),
    )


def _metric(
    metric_id: str,
    experiment_id: str,
    name: str,
    value: float,
    label: str | None,
) -> MetricResponse:
    return MetricResponse(
        id=metric_id,
        experimentId=experiment_id,
        name=name,
        value=value,
        label=label,
        createdAt=datetime(2026, 1, 1),
    )


def test_project_builder_and_immediate_setter_update() -> None:
    client = FakeClient()
    registry = APIRequestsRegistry()
    project = (
        ProjectInstance.builder(request_client=client, api_requests_registry=registry)
        .name("created")
        .description("desc")
        .create()
    )

    assert project.id == PROJECT_ID
    project.name = "renamed"

    assert [(call.method, call.endpoint) for call in client.calls] == [
        ("POST", "/projects"),
        ("PATCH", f"/projects/{PROJECT_ID}"),
    ]
    assert _payload_dict(client.calls[-1].request_payload)["name"] == "renamed"


def test_context_batches_project_updates_once() -> None:
    client = FakeClient()
    registry = APIRequestsRegistry()
    project = ProjectInstance.fetch(
        PROJECT_ID,
        request_client=client,
        api_requests_registry=registry,
    )
    client.calls.clear()

    with project:
        project.name = "batched"
        project.description = "updated"
        assert client.calls == []

    assert len(client.calls) == 1
    assert client.calls[0].method == "PATCH"
    assert _payload_dict(client.calls[0].request_payload) == {
        "name": "batched",
        "description": "updated",
    }


def test_context_exception_skips_pending_update() -> None:
    client = FakeClient()
    registry = APIRequestsRegistry()
    team = TeamInstance.fetch(
        TEAM_ID,
        request_client=client,
        api_requests_registry=registry,
    )
    client.calls.clear()

    try:
        with team:
            team.name = "not-pushed"
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert client.calls == []
    assert team.name == "team"


def test_delete_marks_instance_deleted_and_blocks_updates() -> None:
    client = FakeClient()
    registry = APIRequestsRegistry()
    experiment = ExperimentInstance.fetch(
        EXPERIMENT_ID,
        request_client=client,
        api_requests_registry=registry,
    )
    client.calls.clear()

    experiment.delete()

    assert client.calls[-1].method == "DELETE"
    try:
        experiment.name = "after-delete"
    except ExpTrackerAPIError:
        return
    raise AssertionError("Expected ExpTrackerAPIError after delete")


def test_fetch_helpers_use_id_or_metric_key() -> None:
    client = FakeClient()
    registry = APIRequestsRegistry()

    project = ProjectInstance.fetch(
        UUID(PROJECT_ID), request_client=client, api_requests_registry=registry
    )
    team = TeamInstance.fetch(
        UUID(TEAM_ID), request_client=client, api_requests_registry=registry
    )
    experiment = ExperimentInstance.fetch(
        UUID(EXPERIMENT_ID), request_client=client, api_requests_registry=registry
    )
    metric = MetricInstance.fetch(
        experiment_id=UUID(EXPERIMENT_ID),
        name="accuracy",
        label="final",
        request_client=client,
        api_requests_registry=registry,
    )

    assert project.id == PROJECT_ID
    assert team.id == TEAM_ID
    assert experiment.id == EXPERIMENT_ID
    assert metric.name == "accuracy"
    assert client.calls[-1].endpoint == "/metrics/by-key"
    assert client.calls[-1].query_params == {
        "experimentId": EXPERIMENT_ID,
        "name": "accuracy",
        "label": "final",
    }


def test_metric_builder_and_value_update_use_upsert() -> None:
    client = FakeClient()
    registry = APIRequestsRegistry()
    metric = (
        MetricInstance.builder(request_client=client, api_requests_registry=registry)
        .experiment_id(UUID(EXPERIMENT_ID))
        .name("loss")
        .value(1.0)
        .label("final")
        .create()
    )

    metric.value = 0.25

    assert [(call.method, call.endpoint) for call in client.calls] == [
        ("POST", "/metrics"),
        ("POST", "/metrics"),
    ]
    assert _payload_dict(client.calls[-1].request_payload) == {
        "experimentId": EXPERIMENT_ID,
        "name": "loss",
        "value": 0.25,
        "label": "final",
    }


def test_experiment_builder_and_status_update() -> None:
    client = FakeClient()
    registry = APIRequestsRegistry()
    experiment = (
        ExperimentInstance.builder(request_client=client, api_requests_registry=registry)
        .project_id(UUID(PROJECT_ID))
        .name("run")
        .status(ExperimentStatus.RUNNING)
        .create()
    )

    experiment.status = ExperimentStatus.COMPLETE

    assert experiment.id == EXPERIMENT_ID
    assert client.calls[-1].method == "PATCH"
    assert _payload_dict(client.calls[-1].request_payload) == {
        "status": ExperimentStatus.COMPLETE
    }


def test_uuid_validation_rejects_invalid_write_ids() -> None:
    client = FakeClient()
    registry = APIRequestsRegistry()

    with pytest.raises(ValueError, match="experiment_id must be a valid UUID"):
        MetricInstance.builder(
            request_client=client,
            api_requests_registry=registry,
        ).experiment_id("not-a-uuid")

    assert client.calls == []


def test_experiment_color_validation_accepts_only_hex_colors() -> None:
    client = FakeClient()
    registry = APIRequestsRegistry()

    experiment = (
        ExperimentInstance.builder(request_client=client, api_requests_registry=registry)
        .project_id(PROJECT_ID)
        .name("colored")
        .color("#A1b2C3DD")
        .create()
    )
    assert _payload_dict(client.calls[0].request_payload)["color"] == "#A1b2C3DD"

    with pytest.raises(ValueError, match="color must be a HEX color"):
        ExperimentInstance.builder(
            request_client=client,
            api_requests_registry=registry,
        ).color("red")

    with pytest.raises(ValueError, match="color must be a HEX color"):
        experiment.color = "red"
