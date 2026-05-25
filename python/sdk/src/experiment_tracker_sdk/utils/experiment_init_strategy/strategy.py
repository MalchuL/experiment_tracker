from __future__ import annotations

import random
from uuid import UUID

from experiment_tracker_sdk.client import APIRequestsRegistry, ExperimentTrackerClient
from experiment_tracker_sdk.client.api_access import resolve_client_and_registry
from experiment_tracker_sdk.client.fetching_domain_pages import (
    fetch_all_project_experiments,
    fetch_all_projects,
    fetch_all_teams,
)
from experiment_tracker_sdk.client.instances import (
    ExperimentBuilder,
    ExperimentInstance,
    ProjectBuilder,
    ProjectInstance,
    TeamBuilder,
    TeamInstance,
)
from experiment_tracker_sdk.logger import logger
from experiment_tracker_sdk.utils.experiment_init_strategy.errors import (
    ExperimentAmbiguousError,
    ExperimentInitError,
    ExperimentNotFoundError,
    MultipleItemsResolveError,
    ProjectAmbiguousError,
    ProjectNotFoundError,
    TeamAmbiguousError,
    TeamNotFoundError,
)
from experiment_tracker_sdk.utils.experiment_init_strategy.init_params import InitParams
from experiment_tracker_sdk.utils.experiment_init_strategy.init_result import (
    ExperimentInitResult,
)
from experiment_tracker_sdk.utils.experiment_init_strategy.resolving import (
    MultipleItemsResolveStrategy,
    MultipleResolvingContextObject,
)


class ExperimentInitStrategy:
    """Resolve or create team, project, and experiment objects for a run.

    Args:
        request_client: Optional SDK HTTP client. Defaults to the configured SDK
            client from :func:`resolve_client_and_registry`.
        api_requests_registry: Optional request registry. Defaults to the
            configured SDK registry from :func:`resolve_client_and_registry`.
    """

    def __init__(
        self,
        request_client: ExperimentTrackerClient | None = None,
        api_requests_registry: APIRequestsRegistry | None = None,
    ) -> None:
        resolved = resolve_client_and_registry(
            request_client=request_client,
            api_requests_registry=api_requests_registry,
        )
        self._request_client = resolved.request_client
        self._api_requests_registry = resolved.api_requests_registry
        self._logger = logger.getChild("experiment_init_strategy")

    def init(
        self,
        *,
        experiment_name_or_id: str | UUID,
        project_name_or_id: str | UUID | None = None,
        team_name_or_id: str | UUID | None = None,
        init_params: InitParams = InitParams(),
    ) -> ExperimentInitResult:
        """Resolve or create an experiment and return its instances.

        Args:
            experiment_name_or_id: Experiment name or id to use.
            project_name_or_id: Project name or id to resolve. Required unless
                the caller has another project resolution layer.
            team_name_or_id: Optional team name or id used for project
                filtering and project creation.
            init_params: Creation and ambiguity-resolution options.

        Returns:
            Resolved team, project, and experiment instances.
        """
        experiment_name_or_id = str(experiment_name_or_id)
        project_name_or_id = (
            None if project_name_or_id is None else str(project_name_or_id)
        )
        team_name_or_id = None if team_name_or_id is None else str(team_name_or_id)

        team = self._resolve_team(
            team_name_or_id,
            init_params,
        )
        project = self._resolve_project(
            project_name_or_id,
            team_name_or_id,
            team,
            init_params,
        )
        experiment = self._resolve_experiment(
            experiment_name_or_id,
            project,
            init_params,
        )
        return ExperimentInitResult(
            experiment=experiment,
            project=project,
            team=team,
        )

    @property
    def request_client(self) -> ExperimentTrackerClient:
        """SDK HTTP client used by this strategy."""
        return self._request_client

    @property
    def api_requests_registry(self) -> APIRequestsRegistry:
        """SDK request registry used by this strategy."""
        return self._api_requests_registry

    def _resolve_multiple_items(
        self,
        items: list[MultipleResolvingContextObject],
        strategy: MultipleItemsResolveStrategy,
    ) -> MultipleResolvingContextObject:
        """Resolve one item from multiple matches using ``strategy``.

        Args:
            items: Matching objects wrapped with comparable metadata.
            strategy: Resolution strategy selected by the caller.

        Returns:
            The selected match.
        """
        if not items:
            raise MultipleItemsResolveError("Cannot resolve an empty item list")
        if strategy == MultipleItemsResolveStrategy.FIRST:
            return items[0]
        if strategy == MultipleItemsResolveStrategy.LAST:
            return items[-1]
        if strategy == MultipleItemsResolveStrategy.RANDOM:
            return random.choice(items)
        if strategy == MultipleItemsResolveStrategy.OLDEST:
            return min(items, key=lambda item: item.date)
        if strategy == MultipleItemsResolveStrategy.NEWEST:
            return max(items, key=lambda item: item.date)
        raise MultipleItemsResolveError(f"Multiple items match the name or ID: {items}")

    def _select_one(
        self,
        matches: list[MultipleResolvingContextObject],
        *,
        strategy: MultipleItemsResolveStrategy,
        ambiguous_error: type[ExperimentInitError],
    ) -> MultipleResolvingContextObject:
        """Select one matching object or raise for ambiguity."""
        if len(matches) == 1:
            return matches[0]
        if strategy == MultipleItemsResolveStrategy.ERROR:
            raise ambiguous_error(f"Multiple items match the name or ID: {matches}")
        return self._resolve_multiple_items(matches, strategy)

    @staticmethod
    def _looks_like_id(value: str) -> bool:
        """Return whether ``value`` parses as a UUID."""
        try:
            UUID(value)
        except ValueError:
            return False
        return True

    def _raise_if_name_looks_like_id(
        self,
        *,
        name_or_id: str,
        item_label: str,
        error: type[ExperimentInitError],
        init_params: InitParams,
    ) -> None:
        """Prevent accidental creation when a missing lookup value is ID-like."""
        if init_params.error_if_name_looks_like_id and self._looks_like_id(name_or_id):
            raise error(
                f"{item_label} name looks like an ID, but no existing "
                f"{item_label.lower()} was found: {name_or_id}"
            )

    def _resolve_team(
        self,
        team_name_or_id: str | None,
        init_params: InitParams,
    ) -> TeamInstance | None:
        """Resolve or create a team and return its instance."""
        # If None this means we don't have a team for project
        if team_name_or_id is None:
            return None
        # We try to use existing team first, if not found we create a new one
        if not init_params.try_existing_team:
            if not init_params.create_team_if_not_exists:
                raise TeamNotFoundError(f"Team not found: {team_name_or_id}")
            # We raise an error if the name looks like an ID (and if we are not allowed to such names)
            # This is to prevent accidental creation when a missing lookup value is ID-like
            self._raise_if_name_looks_like_id(
                name_or_id=team_name_or_id,
                item_label="Team",
                error=TeamNotFoundError,
                init_params=init_params,
            )
            return self._create_team(team_name=team_name_or_id)
        # We will try to find an existing team by name or id and use it if found
        teams = fetch_all_teams(
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )
        matches = [
            MultipleResolvingContextObject(
                item=team,
                date=team.createdAt,
                id=str(team.id),
                name=team.name,
            )
            for team in teams
            if team.name == team_name_or_id or str(team.id) == team_name_or_id
        ]
        # If no matches are found, we create a new team
        if not matches:
            # We check if we should create a new team
            if not init_params.create_team_if_not_exists:
                raise TeamNotFoundError(f"Team not found: {team_name_or_id}")
            # We raise an error if the name looks like an ID (and if we are not allowed to such names)
            # This is to prevent accidental creation when a missing lookup value is ID-like
            self._raise_if_name_looks_like_id(
                name_or_id=team_name_or_id,
                item_label="Team",
                error=TeamNotFoundError,
                init_params=init_params,
            )
            self._logger.info(f"Creating team: {team_name_or_id}")
            return self._create_team(team_name=team_name_or_id)
        # We select the team from the matches (by using the strategy)
        match = self._select_one(
            matches,
            strategy=init_params.multiple_items_resolve_strategy,
            ambiguous_error=TeamAmbiguousError,
        )
        return TeamInstance._from_response(
            match.item,
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )

    def _resolve_project(
        self,
        project_name_or_id: str | None,
        team_name_or_id: str | None,
        team: TeamInstance | None,
        init_params: InitParams,
    ) -> ProjectInstance:
        """Resolve or create a project and return its instance."""
        # If None this means we don't have a project for experiment
        if project_name_or_id is None:
            raise ProjectNotFoundError("Project name or id is required")
        # We try to use existing project first, if not found we create a new one
        if not init_params.try_existing_project:
            # We check if we should create a new project
            if not init_params.create_project_if_not_exists:
                raise ProjectNotFoundError(f"Project not found: {project_name_or_id}")
            # We raise an error if the name looks like an ID (and if we are not allowed to such names)
            # This is to prevent accidental creation when a missing lookup value is ID-like
            self._raise_if_name_looks_like_id(
                name_or_id=project_name_or_id,
                item_label="Project",
                error=ProjectNotFoundError,
                init_params=init_params,
            )
            # We create a new project
            return self._create_project(
                project_name=project_name_or_id,
                team_id=None if team is None else team.id,
            )
        # We will try to find an existing project by name or id and use it if found
        projects = fetch_all_projects(
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )
        matches = []
        for project in projects:
            # If doesn't match the name or id, we skip
            if (
                project.name != project_name_or_id
                and str(project.id) != project_name_or_id
            ):
                continue
            # If we have a team
            if team_name_or_id is not None:
                # Because team_name_or_id is not None, we expect to have a team
                if project.team is None:
                    continue
                team_id = None if team is None else team.id
                # We assume that the team id is the same as the project team id
                # TODO add to project team_id field
                # If id or name doesn't match, we skip
                if (
                    str(project.team.id) != team_id
                    and project.team.name != team_name_or_id
                ):
                    continue
            matches.append(
                MultipleResolvingContextObject(
                    item=project,
                    date=project.createdAt,
                    id=str(project.id),
                    name=project.name,
                )
            )
        if not matches:
            # If we don't want to create a new project, we raise an error
            if not init_params.create_project_if_not_exists:
                raise ProjectNotFoundError(f"Project not found: {project_name_or_id}")
            # We raise an error if the name looks like an ID (and if we are not allowed to such names)
            # This is to prevent accidental creation when a missing lookup value is ID-like
            self._raise_if_name_looks_like_id(
                name_or_id=project_name_or_id,
                item_label="Project",
                error=ProjectNotFoundError,
                init_params=init_params,
            )
            # We create a new project
            self._logger.info(f"Creating project: {project_name_or_id}")
            return self._create_project(
                project_name=project_name_or_id,
                team_id=None if team is None else team.id,
            )
        # We select the project from the matches (by using the strategy)
        match = self._select_one(
            matches,
            strategy=init_params.multiple_items_resolve_strategy,
            ambiguous_error=ProjectAmbiguousError,
        )
        return ProjectInstance._from_response(
            match.item,
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )

    def _create_team(self, team_name: str) -> TeamInstance:
        """Create a team and return its instance."""
        self._logger.info(f"Creating team: {team_name}")
        return (
            TeamBuilder(
                request_client=self._request_client,
                api_requests_registry=self._api_requests_registry,
            )
            .name(team_name)
            .create()
        )

    def _create_project(
        self, project_name: str, team_id: str | None
    ) -> ProjectInstance:
        """Create a project and return its instance."""
        self._logger.info(f"Creating project: {project_name}")
        builder = ProjectBuilder(
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        ).name(project_name)
        if team_id:
            builder.team_id(team_id)
        return builder.create()

    def _resolve_experiment(
        self,
        experiment_name_or_id: str,
        project: ProjectInstance,
        init_params: InitParams,
    ) -> ExperimentInstance:
        """Resolve or create an experiment and return its instance."""
        # If None this means we don't have an experiment for project
        if not init_params.try_existing_experiment:
            # If we don't want to create a new experiment, we raise an error
            if not init_params.create_experiment_if_not_exists:
                raise ExperimentNotFoundError(
                    f"Experiment not found: {experiment_name_or_id}"
                )
            # We raise an error if the name looks like an ID (and if we are not allowed to such names)
            # This is to prevent accidental creation when a missing lookup value is ID-like
            self._raise_if_name_looks_like_id(
                name_or_id=experiment_name_or_id,
                item_label="Experiment",
                error=ExperimentNotFoundError,
                init_params=init_params,
            )
            return self._create_experiment(experiment_name_or_id, project.id)
        # We will try to find an existing experiment by name or id and use it if found
        experiments = fetch_all_project_experiments(
            project_id=project.id,
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )
        # We create a list of matches (by using the strategy)
        matches = [
            MultipleResolvingContextObject(
                item=experiment,
                date=experiment.createdAt,
                id=str(experiment.id),
                name=experiment.name,
            )
            for experiment in experiments
            if experiment.name == experiment_name_or_id
            or str(experiment.id) == experiment_name_or_id
        ]
        # If no matches are found, we create a new experiment
        if not matches:
            # If we don't want to create a new experiment, we raise an error
            if not init_params.create_experiment_if_not_exists:
                raise ExperimentNotFoundError(
                    f"Experiment not found: {experiment_name_or_id}"
                )
            # We raise an error if the name looks like an ID (and if we are not allowed to such names)
            # This is to prevent accidental creation when a missing lookup value is ID-like
            self._raise_if_name_looks_like_id(
                name_or_id=experiment_name_or_id,
                item_label="Experiment",
                error=ExperimentNotFoundError,
                init_params=init_params,
            )
            self._logger.info(
                f"Creating experiment: {experiment_name_or_id} for project: {project.id}"
            )
            return self._create_experiment(experiment_name_or_id, project.id)
        match = self._select_one(
            matches,
            strategy=init_params.multiple_items_resolve_strategy,
            ambiguous_error=ExperimentAmbiguousError,
        )
        return ExperimentInstance._from_response(
            match.item,
            request_client=self._request_client,
            api_requests_registry=self._api_requests_registry,
        )

    def _create_experiment(
        self,
        experiment_name: str,
        project_id: str,
    ) -> ExperimentInstance:
        """Create an experiment and return its instance."""
        builder = (
            ExperimentBuilder(
                request_client=self._request_client,
                api_requests_registry=self._api_requests_registry,
            )
            .project_id(project_id)
            .name(experiment_name)
        )
        return builder.create()
