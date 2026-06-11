from __future__ import annotations

from typing import cast
from uuid import UUID

from experiment_tracker_sdk.client.api_access import resolve_client_and_registry
from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.client import ExperimentTrackerClient
from experiment_tracker_sdk.client.domain.experiments.dto import ExperimentResponse
from experiment_tracker_sdk.client.domain.projects.dto import ProjectResponse
from experiment_tracker_sdk.client.domain.teams.dto import TeamListItemResponse

from .utils.fetching_utils import DEFAULT_FETCH_LIMIT, fetch_all_requests


def fetch_all_projects(
    *,
    limit: int = DEFAULT_FETCH_LIMIT,
    request_client: ExperimentTrackerClient | None = None,
    api_requests_registry: APIRequestsRegistry | None = None,
) -> list[ProjectResponse]:
    """Fetch all projects visible to the current SDK credentials.

    Args:
        limit: Maximum number of projects to request per page.
        request_client: Optional SDK HTTP client used to execute request specs.
            Defaults to the shared SDK API access client.
        api_requests_registry: Optional registry that provides project request
            spec factories. Defaults to the shared SDK API access registry.

    Returns:
        A flat list of all visible projects, in the order returned by the
        paginated API.

    Raises:
        TypeError: If the SDK request does not return a paginated response.
        ValueError: If ``limit`` is not positive.
        AttributeError: If a page does not expose ``hasNext`` or ``has_next``.
        RuntimeError: If a page reports another page but returns zero items.
    """
    resolved = resolve_client_and_registry(
        request_client,
        api_requests_registry,
    )
    return cast(
        list[ProjectResponse],
        fetch_all_requests(
            resolved.request_client.request,
            resolved.api_requests_registry.projects.get_all_projects,
            limit=limit,
        ),
    )


def fetch_all_project_experiments(
    project_id: str | UUID,
    *,
    search: str | None = None,
    include_features: bool = True,
    limit: int = DEFAULT_FETCH_LIMIT,
    request_client: ExperimentTrackerClient | None = None,
    api_requests_registry: APIRequestsRegistry | None = None,
) -> list[ExperimentResponse]:
    """Fetch all experiments in one project.

    Args:
        project_id: Project UUID or UUID string whose experiments should be
            fetched.
        search: Optional server-side substring filter for experiment id, name,
            description, and tags.
        include_features: Whether experiment list rows should include feature
            trees. Set to ``False`` for lighter list payloads.
        limit: Maximum number of experiments to request per page.
        request_client: Optional SDK HTTP client used to execute request specs.
            Defaults to the shared SDK API access client.
        api_requests_registry: Optional registry that provides experiment
            request spec factories. Defaults to the shared SDK API access
            registry.

    Returns:
        A flat list of all matching experiments in the project, in the order
        returned by the paginated API.

    Raises:
        TypeError: If the SDK request does not return a paginated response.
        ValueError: If ``limit`` is not positive.
        AttributeError: If a page does not expose ``hasNext`` or ``has_next``.
        RuntimeError: If a page reports another page but returns zero items.
    """
    resolved = resolve_client_and_registry(
        request_client,
        api_requests_registry,
    )
    project_id = str(project_id)

    def make_request_spec(*, limit: int, offset: int):
        return resolved.api_requests_registry.experiments.get_experiments_by_project(
            project_id,
            limit=limit,
            offset=offset,
            search=search,
            include_features=include_features,
        )

    return cast(
        list[ExperimentResponse],
        fetch_all_requests(
            resolved.request_client.request,
            make_request_spec,
            limit=limit,
        ),
    )


def fetch_all_recent_experiments(
    project_id: str | UUID,
    *,
    include_features: bool = True,
    limit: int = DEFAULT_FETCH_LIMIT,
    request_client: ExperimentTrackerClient | None = None,
    api_requests_registry: APIRequestsRegistry | None = None,
) -> list[ExperimentResponse]:
    """Fetch all recent experiments for one project.

    Args:
        project_id: Project UUID or UUID string whose recent experiments should
            be fetched.
        include_features: Whether experiment list rows should include feature
            trees. Set to ``False`` for lighter list payloads.
        limit: Maximum number of experiments to request per page.
        request_client: Optional SDK HTTP client used to execute request specs.
            Defaults to the shared SDK API access client.
        api_requests_registry: Optional registry that provides experiment
            request spec factories. Defaults to the shared SDK API access
            registry.

    Returns:
        A flat list of all recent experiments for the project, in the order
        returned by the paginated API.

    Raises:
        TypeError: If the SDK request does not return a paginated response.
        ValueError: If ``limit`` is not positive.
        AttributeError: If a page does not expose ``hasNext`` or ``has_next``.
        RuntimeError: If a page reports another page but returns zero items.
    """
    resolved = resolve_client_and_registry(
        request_client,
        api_requests_registry,
    )
    project_id = str(project_id)

    def make_request_spec(*, limit: int, offset: int):
        return resolved.api_requests_registry.experiments.get_recent_experiments(
            project_id,
            limit=limit,
            offset=offset,
            include_features=include_features,
        )

    return cast(
        list[ExperimentResponse],
        fetch_all_requests(
            resolved.request_client.request,
            make_request_spec,
            limit=limit,
        ),
    )


def fetch_all_teams(
    *,
    limit: int = DEFAULT_FETCH_LIMIT,
    request_client: ExperimentTrackerClient | None = None,
    api_requests_registry: APIRequestsRegistry | None = None,
) -> list[TeamListItemResponse]:
    """Fetch all teams visible to the current SDK credentials.

    Args:
        limit: Maximum number of teams to request per page.
        request_client: Optional SDK HTTP client used to execute request specs.
            Defaults to the shared SDK API access client.
        api_requests_registry: Optional registry that provides team request spec
            factories. Defaults to the shared SDK API access registry.

    Returns:
        A flat list of all visible teams, including list-row permission hints
        such as ``canCreateProject``.

    Raises:
        TypeError: If the SDK request does not return a paginated response.
        ValueError: If ``limit`` is not positive.
        AttributeError: If a page does not expose ``hasNext`` or ``has_next``.
        RuntimeError: If a page reports another page but returns zero items.
    """
    resolved = resolve_client_and_registry(
        request_client,
        api_requests_registry,
    )
    return cast(
        list[TeamListItemResponse],
        fetch_all_requests(
            resolved.request_client.request,
            resolved.api_requests_registry.teams.get_all_teams,
            limit=limit,
        ),
    )
