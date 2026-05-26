"""Named experiment artifact resource CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import click

from experiment_tracker_sdk.client.request_types import FileDownloadResponse
from experiment_tracker_sdk.client.utils.downloading import dump_binary_content_to_path

from .common import (
    api,
    build_file_upload,
    confirm_delete,
    echo_yaml,
    require_identifier,
)


@click.group("experiment-artifact", short_help="Manage named experiment artifacts")
def experiment_artifact_group() -> None:
    """Manage named experiment artifacts."""


@experiment_artifact_group.command("list")
@click.option("-e", "--experiment-id", required=True)
@click.option("-p", "--filepath", "filepaths", multiple=True)
@click.option("-l", "--limit", type=int, default=None)
@click.option("-o", "--offset", type=int, default=None)
def experiment_artifact_list_command(
    experiment_id: str,
    filepaths: tuple[str, ...],
    limit: int | None,
    offset: int | None,
) -> None:
    client, registry = api()
    echo_yaml(
        client.request(
            registry.experiment_artifacts.list_named_experiment_artifacts(
                experiment_id=experiment_id,
                file_paths=list(filepaths) if filepaths else None,
                limit=limit,
                offset=offset,
            )
        )
    )


@experiment_artifact_group.command("get")
@click.option("-e", "--experiment-id", required=True)
@click.option("-p", "--filepath", default=None)
@click.option("-b", "--blob-id", default=None)
@click.option("-H", "--artifact-hash", default=None)
def experiment_artifact_get_command(
    experiment_id: str,
    filepath: str | None,
    blob_id: str | None,
    artifact_hash: str | None,
) -> None:
    require_identifier(filepath, blob_id, artifact_hash)
    client, registry = api()
    echo_yaml(
        client.request(
            registry.experiment_artifacts.get_named_experiment_artifact(
                experiment_id=experiment_id,
                filepath=filepath,
                blob_id=blob_id,
                artifact_hash=artifact_hash,
            )
        )
    )


@experiment_artifact_group.command("upsert")
@click.option("-e", "--experiment-id", required=True)
@click.option(
    "-F",
    "--file",
    "file_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("-p", "--filepath", required=True)
@click.option("-n", "--name", default=None)
def experiment_artifact_upsert_command(
    experiment_id: str,
    file_path: Path,
    filepath: str,
    name: str | None,
) -> None:
    client, registry = api()
    echo_yaml(
        client.request(
            registry.experiment_artifacts.upsert_named_experiment_artifact(
                experiment_id=experiment_id,
                filepath=filepath,
                file=build_file_upload(file_path),
                name=name,
            )
        )
    )


@experiment_artifact_group.command("download")
@click.option("-e", "--experiment-id", required=True)
@click.option("-p", "--filepath", default=None)
@click.option("-b", "--blob-id", default=None)
@click.option("-H", "--artifact-hash", default=None)
@click.option(
    "-O",
    "--output",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
)
def experiment_artifact_download_command(
    experiment_id: str,
    filepath: str | None,
    blob_id: str | None,
    artifact_hash: str | None,
    output_path: Path,
) -> None:
    require_identifier(filepath, blob_id, artifact_hash)
    client, registry = api()
    download = cast(
        FileDownloadResponse,
        client.request(
            registry.experiment_artifacts.download_named_experiment_artifact(
                experiment_id=experiment_id,
                filepath=filepath,
                blob_id=blob_id,
                artifact_hash=artifact_hash,
            )
        ),
    )
    destination = dump_binary_content_to_path(
        download.content,
        output_path,
        download.filename,
    )
    click.echo(str(destination))


@experiment_artifact_group.command("delete")
@click.option("-e", "--experiment-id", required=True)
@click.option("-p", "--filepath", default=None)
@click.option("-b", "--blob-id", default=None)
@click.option("-H", "--artifact-hash", default=None)
@click.option("-y", "--yes", is_flag=True)
def experiment_artifact_delete_command(
    experiment_id: str,
    filepath: str | None,
    blob_id: str | None,
    artifact_hash: str | None,
    yes: bool,
) -> None:
    require_identifier(filepath, blob_id, artifact_hash)
    confirm_delete(yes, f"Delete experiment artifact for experiment {experiment_id}?")
    client, registry = api()
    echo_yaml(
        client.request(
            registry.experiment_artifacts.delete_named_experiment_artifacts(
                experiment_id=experiment_id,
                filepath=filepath,
                blob_id=blob_id,
                artifact_hash=artifact_hash,
            )
        )
    )

