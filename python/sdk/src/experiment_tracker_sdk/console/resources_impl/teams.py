"""Team resource CLI commands."""

from __future__ import annotations

import click

from .common import api, confirm_delete, echo_yaml


@click.group("team", short_help="Manage teams")
def team_group() -> None:
    """Manage teams."""


@team_group.command("list")
@click.option("-l", "--limit", type=int, default=None)
@click.option("-o", "--offset", type=int, default=None)
def team_list_command(limit: int | None, offset: int | None) -> None:
    client, registry = api()
    echo_yaml(client.request(registry.teams.get_all_teams(limit, offset)))


@team_group.command("get")
@click.argument("team_id")
def team_get_command(team_id: str) -> None:
    client, registry = api()
    echo_yaml(client.request(registry.teams.get_team(team_id)))


@team_group.command("create")
@click.option("-n", "--name", required=True)
@click.option("-d", "--description", default=None)
def team_create_command(name: str, description: str | None) -> None:
    client, registry = api()
    echo_yaml(
        client.request(registry.teams.create_team(name=name, description=description))
    )


@team_group.command("update")
@click.argument("team_id")
@click.option("-n", "--name", required=True)
@click.option("-d", "--description", default=None)
def team_update_command(team_id: str, name: str, description: str | None) -> None:
    client, registry = api()
    echo_yaml(
        client.request(
            registry.teams.update_team(
                team_id=team_id,
                name=name,
                description=description,
            )
        )
    )


@team_group.command("delete")
@click.argument("team_id")
@click.option("-y", "--yes", is_flag=True)
def team_delete_command(team_id: str, yes: bool) -> None:
    confirm_delete(yes, f"Delete team {team_id}?")
    client, registry = api()
    echo_yaml(client.request(registry.teams.delete_team(team_id)))

