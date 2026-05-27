"""Experiment resource CLI commands."""

from __future__ import annotations

import click

from experiment_tracker_sdk.client.constants import UNSET
from experiment_tracker_sdk.client.domain.experiments.dto import ExperimentStatus

from .common import api, confirm_delete, echo_yaml


@click.group("experiment", short_help="Manage experiments")
def experiment_group() -> None:
    """Manage experiments."""


@experiment_group.command("list")
@click.option("-p", "--project-id", required=True)
@click.option("-l", "--limit", type=int, default=None)
@click.option("-o", "--offset", type=int, default=None)
@click.option("-n", "--name", "search", default=None)
def experiment_list_command(
    project_id: str,
    limit: int | None,
    offset: int | None,
    search: str | None,
) -> None:
    client, registry = api()
    echo_yaml(
        client.request(
            registry.experiments.get_experiments_by_project(
                project_id=project_id,
                limit=limit,
                offset=offset,
                search=search,
                include_features=False,
            )
        )
    )


@experiment_group.command("get")
@click.argument("experiment_id")
def experiment_get_command(experiment_id: str) -> None:
    client, registry = api()
    echo_yaml(client.request(registry.experiments.get_experiment(experiment_id)))


@experiment_group.command("create")
@click.option("-p", "--project-id", required=True)
@click.option("-n", "--name", required=True)
@click.option("-d", "--description", default="")
@click.option(
    "-s",
    "--status",
    type=click.Choice([status.value for status in ExperimentStatus]),
    default=ExperimentStatus.PLANNED.value,
)
@click.option("-c", "--color", default=None)
@click.option("-P", "--parent-experiment-id", default=None)
@click.option("-g", "--tag", "tags", multiple=True)
def experiment_create_command(
    project_id: str,
    name: str,
    description: str,
    status: str,
    color: str | None,
    parent_experiment_id: str | None,
    tags: tuple[str, ...],
) -> None:
    client, registry = api()
    echo_yaml(
        client.request(
            registry.experiments.create_experiment(
                project_id=project_id,
                name=name,
                description=description,
                status=ExperimentStatus(status),
                color=color,
                parent_experiment_id=parent_experiment_id,
                tags=list(tags) if tags else None,
            )
        )
    )


@experiment_group.command("update")
@click.argument("experiment_id")
@click.option("-n", "--name", default=None)
@click.option("-d", "--description", default=None)
@click.option(
    "-s",
    "--status",
    type=click.Choice([status.value for status in ExperimentStatus]),
    default=None,
)
@click.option("-c", "--color", default=None)
@click.option("-r", "--progress", type=int, default=None)
@click.option("-P", "--parent-experiment-id", default=None)
@click.option("-g", "--tag", "tags", multiple=True)
def experiment_update_command(
    experiment_id: str,
    name: str | None,
    description: str | None,
    status: str | None,
    color: str | None,
    progress: int | None,
    parent_experiment_id: str | None,
    tags: tuple[str, ...],
) -> None:
    client, registry = api()
    echo_yaml(
        client.request(
            registry.experiments.update_experiment(
                experiment_id=experiment_id,
                name=UNSET if name is None else name,
                description=UNSET if description is None else description,
                status=UNSET if status is None else ExperimentStatus(status),
                color=UNSET if color is None else color,
                progress=UNSET if progress is None else progress,
                parent_experiment_id=(
                    UNSET if parent_experiment_id is None else parent_experiment_id
                ),
                tags=list(tags) if tags else UNSET,
            )
        )
    )


@experiment_group.command("delete")
@click.argument("experiment_id")
@click.option("-y", "--yes", is_flag=True)
def experiment_delete_command(experiment_id: str, yes: bool) -> None:
    confirm_delete(yes, f"Delete experiment {experiment_id}?")
    client, registry = api()
    echo_yaml(client.request(registry.experiments.delete_experiment(experiment_id)))

