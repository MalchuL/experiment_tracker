from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from experiment_tracker_sdk.client import APIRequestsRegistry, ExperimentTrackerClient
from experiment_tracker_sdk.client.request_types import ApiRequestSpec
from experiment_tracker_sdk.utils.experiment_init_strategy import InitParams
from experiment_tracker_sdk.utils.experiment_init_strategy.errors import (
    ExperimentNotFoundError,
    ProjectNotFoundError,
    TeamNotFoundError,
)
from experiment_tracker_sdk.utils.experiment_init_strategy.strategy import (
    ExperimentInitStrategy,
)


ID_LIKE_NAME = "11111111-1111-4111-8111-111111111111"


class FakeClient:
    def request(self, spec: ApiRequestSpec[Any]) -> Any:
        raise AssertionError(f"Unexpected request: {spec.endpoint}")


@dataclass(frozen=True)
class FakeProject:
    id: str


def _strategy() -> ExperimentInitStrategy:
    return ExperimentInitStrategy(
        request_client=cast(ExperimentTrackerClient, FakeClient()),
        api_requests_registry=APIRequestsRegistry(),
    )


def test_try_existing_team_raises_before_creating_id_like_name(monkeypatch: Any) -> None:
    strategy = _strategy()
    monkeypatch.setattr(
        "experiment_tracker_sdk.utils.experiment_init_strategy.strategy.fetch_all_teams",
        lambda **_: [],
    )
    monkeypatch.setattr(
        strategy,
        "_create_team",
        lambda name: pytest.fail(f"Unexpected team creation for {name}"),
    )

    with pytest.raises(TeamNotFoundError, match="looks like an ID"):
        strategy._resolve_team(
            ID_LIKE_NAME,
            InitParams(create_team_if_not_exists=True),
        )


def test_try_existing_project_raises_before_creating_id_like_name(
    monkeypatch: Any,
) -> None:
    strategy = _strategy()
    monkeypatch.setattr(
        "experiment_tracker_sdk.utils.experiment_init_strategy.strategy.fetch_all_projects",
        lambda **_: [],
    )
    monkeypatch.setattr(
        strategy,
        "_create_project",
        lambda name, team_id: pytest.fail(
            f"Unexpected project creation for {name} in team {team_id}"
        ),
    )

    with pytest.raises(ProjectNotFoundError, match="looks like an ID"):
        strategy._resolve_project(
            ID_LIKE_NAME,
            None,
            None,
            InitParams(create_project_if_not_exists=True),
        )


def test_try_existing_experiment_raises_before_creating_id_like_name(
    monkeypatch: Any,
) -> None:
    strategy = _strategy()
    monkeypatch.setattr(
        "experiment_tracker_sdk.utils.experiment_init_strategy.strategy.fetch_all_project_experiments",
        lambda **_: [],
    )
    monkeypatch.setattr(
        strategy,
        "_create_experiment",
        lambda name, project_id: pytest.fail(
            f"Unexpected experiment creation for {name} in project {project_id}"
        ),
    )

    with pytest.raises(ExperimentNotFoundError, match="looks like an ID"):
        strategy._resolve_experiment(
            ID_LIKE_NAME,
            cast(Any, FakeProject(id="project-1")),
            InitParams(create_experiment_if_not_exists=True),
        )


def test_id_like_name_guard_can_be_disabled(monkeypatch: Any) -> None:
    strategy = _strategy()
    created = object()
    monkeypatch.setattr(
        "experiment_tracker_sdk.utils.experiment_init_strategy.strategy.fetch_all_project_experiments",
        lambda **_: [],
    )
    monkeypatch.setattr(
        strategy,
        "_create_experiment",
        lambda name, project_id: created,
    )

    result = strategy._resolve_experiment(
        ID_LIKE_NAME,
        cast(Any, FakeProject(id="project-1")),
        InitParams(
            create_experiment_if_not_exists=True,
            error_if_name_looks_like_id=False,
        ),
    )

    assert result is created


def test_direct_create_team_raises_for_id_like_name(monkeypatch: Any) -> None:
    strategy = _strategy()
    monkeypatch.setattr(
        strategy,
        "_create_team",
        lambda name: pytest.fail(f"Unexpected team creation for {name}"),
    )

    with pytest.raises(TeamNotFoundError, match="looks like an ID"):
        strategy._resolve_team(
            ID_LIKE_NAME,
            InitParams(
                try_existing_team=False,
                create_team_if_not_exists=True,
            ),
        )


def test_direct_create_project_raises_for_id_like_name(monkeypatch: Any) -> None:
    strategy = _strategy()
    monkeypatch.setattr(
        strategy,
        "_create_project",
        lambda name, team_id: pytest.fail(
            f"Unexpected project creation for {name} in team {team_id}"
        ),
    )

    with pytest.raises(ProjectNotFoundError, match="looks like an ID"):
        strategy._resolve_project(
            ID_LIKE_NAME,
            None,
            None,
            InitParams(
                try_existing_project=False,
                create_project_if_not_exists=True,
            ),
        )


def test_direct_create_experiment_raises_for_id_like_name(
    monkeypatch: Any,
) -> None:
    strategy = _strategy()
    monkeypatch.setattr(
        strategy,
        "_create_experiment",
        lambda name, project_id: pytest.fail(
            f"Unexpected experiment creation for {name} in project {project_id}"
        ),
    )

    with pytest.raises(ExperimentNotFoundError, match="looks like an ID"):
        strategy._resolve_experiment(
            ID_LIKE_NAME,
            cast(Any, FakeProject(id="project-1")),
            InitParams(
                try_existing_experiment=False,
                create_experiment_if_not_exists=True,
            ),
        )
