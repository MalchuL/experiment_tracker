"""Project resource CLI commands."""

from __future__ import annotations

import click

from .common import api, confirm_delete, echo_yaml


@click.group("project", short_help="Manage projects")
def project_group() -> None:
    """Manage projects."""


@project_group.command("list")
@click.option("-l", "--limit", type=int, default=None)
@click.option("-o", "--offset", type=int, default=None)
def project_list_command(limit: int | None, offset: int | None) -> None:
    client, registry = api()
    echo_yaml(client.request(registry.projects.get_all_projects(limit, offset)))


@project_group.command("get")
@click.argument("project_id")
def project_get_command(project_id: str) -> None:
    client, registry = api()
    echo_yaml(client.request(registry.projects.get_project(project_id)))


@project_group.command("settings")
@click.argument("project_id")
def project_settings_command(project_id: str) -> None:
    client, registry = api()
    echo_yaml(client.request(registry.projects.get_project_settings_map(project_id)))


@project_group.command("create")
@click.option("-n", "--name", required=True)
@click.option("-d", "--description", default="")
@click.option("-t", "--team-id", default=None)
def project_create_command(
    name: str,
    description: str,
    team_id: str | None,
) -> None:
    client, registry = api()
    echo_yaml(
        client.request(
            registry.projects.create_project(
                name=name,
                description=description,
                team_id=team_id,
            )
        )
    )


@project_group.command("update")
@click.argument("project_id")
@click.option("-n", "--name", default=None)
@click.option("-d", "--description", default=None)
def project_update_command(
    project_id: str,
    name: str | None,
    description: str | None,
) -> None:
    client, registry = api()
    echo_yaml(
        client.request(
            registry.projects.update_project(
                project_id=project_id,
                name=name,
                description=description,
            )
        )
    )


@project_group.command("delete")
@click.argument("project_id")
@click.option("-y", "--yes", is_flag=True)
def project_delete_command(project_id: str, yes: bool) -> None:
    confirm_delete(yes, f"Delete project {project_id}?")
    client, registry = api()
    echo_yaml(client.request(registry.projects.delete_project(project_id)))
