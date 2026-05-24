from dataclasses import dataclass
from datetime import datetime
import random
from typing import Any
from experiment_tracker_sdk import ExpTracker
from experiment_tracker_sdk.client import APIRequestsRegistry, ExperimentTrackerClient
from experiment_tracker_sdk.client.api_access import resolve_client_and_registry
from experiment_tracker_sdk.client.fetching_domain_pages import (
    fetch_all_projects,
    fetch_all_project_experiments,
    fetch_all_teams,
)
from enum import Enum
from experiment_tracker_sdk.logger import logger


class MultipleItemsResolveStrategy(Enum):
    ERROR = "error"
    FIRST = "first"
    LAST = "last"
    RANDOM = "random"
    OLDEST = "oldest"
    NEWEST = "newest"


@dataclass(frozen=True)
class MultipleResolvingContextObject:
    item: Any
    date: datetime
    id: str
    name: str


@dataclass(frozen=True)
class InitParams:
    create_project_if_not_exists: bool = False
    create_experiment_if_not_exists: bool = False
    create_team_if_not_exists: bool = False
    multiple_items_resolve_strategy: MultipleItemsResolveStrategy = (
        MultipleItemsResolveStrategy.ERROR
    )


class RunSample:
    def __init__(
        self,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ):
        self.exp_tracker = None
        resolved = resolve_client_and_registry(
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )
        self._request_client = resolved.request_client
        self._api_requests_registry = resolved.api_requests_registry
        self._logger = logger.getChild("runner")
        
    def _resolve_multiple_items(self, items: list[MultipleResolvingContextObject], strategy: MultipleItemsResolveStrategy) -> MultipleResolvingContextObject:
        if strategy == MultipleItemsResolveStrategy.FIRST:
            return items[0]
        if strategy == MultipleItemsResolveStrategy.LAST:
            return items[-1]
        if strategy == MultipleItemsResolveStrategy.RANDOM:
            return random.choice(items)
        if strategy == MultipleItemsResolveStrategy.OLDEST:
            return min(items, key=lambda x: x.date)
        if strategy == MultipleItemsResolveStrategy.NEWEST:
            return max(items, key=lambda x: x.date)
        # Error case
        raise MultipleItemsResolveError(f"Multiple items match the name or ID: {items}")

    def init(
        self,
        project_name_or_id: str,
        experiment_name_or_id: str,
        team_name_or_id: str | None = None,
        init_params: InitParams = InitParams(),
    ) -> None:
        """Initialize the RunSample instance.
        Args:
            project_name_or_id (str): The name or ID of the project.
            experiment_name_or_id (str): The name or ID of the experiment.
            team_name_or_id (str | None): The name or ID of the team.
        """
        # Fetch projects
        projects = fetch_all_projects(
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )
        projects_matching = [
            (p for p in projects if p.name == project_name_or_id or p.id == project_name_or_id),
        ]
        if len(projects_matching) > 1:
            self._logger.warning(f"Multiple projects match the name or ID: {project_name_or_id}. Try to resolve with the strategy: {init_params.multiple_items_resolve_strategy}")
            project_obj = self._resolve_multiple_items(projects_matching, init_params.multiple_items_resolve_strategy)
        if len(projects_matching) == 0:
            if init_params.create_project_if_not_exists:
                self._logger.info(f"Creating project: {project_name_or_id}")
        if project_obj is None:
            raise ProjectNotFoundError(f"Project not found: {project_name_or_id}")
        if init_params.
        self._logger.info("Fetching projects")
        projects = 
        self.exp_tracker = ExpTracker.init(
            project=project_name_or_id,
            experiment=experiment_name_or_id,
            team=team_name_or_id,
        )
