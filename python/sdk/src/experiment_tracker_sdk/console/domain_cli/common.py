"""Shared helpers for resource CLI commands."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

import click
from pydantic import BaseModel

from experiment_tracker_sdk.client.api_access import ExpTrackerApiAccess
from experiment_tracker_sdk.client.request_types import FileUploadSpec
from experiment_tracker_sdk.error import ExpTrackerConfigError


def api() -> tuple[Any, Any]:
    try:
        access = ExpTrackerApiAccess.instance()
        return access.request_client, access.api_requests_registry
    except ExpTrackerConfigError as exc:
        raise click.UsageError(
            "Config not found. Run `experiment-tracker init`."
        ) from exc


def model_to_plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [model_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: model_to_plain(item) for key, item in value.items()}
    return value


def _yaml_key(value: Any) -> str:
    text = str(value)
    if text.replace("_", "").replace("-", "").isalnum():
        return text
    return json.dumps(text, ensure_ascii=False)


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "{}" if not value else json.dumps(value, default=str, ensure_ascii=False)
    if isinstance(value, list):
        return "[]" if not value else json.dumps(value, default=str, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _yaml_lines(value: Any, indent: int = 0) -> list[str]:
    plain = model_to_plain(value)
    prefix = " " * indent
    if isinstance(plain, dict):
        if not plain:
            return [f"{prefix}{{}}"]
        lines: list[str] = []
        for key, item in plain.items():
            if isinstance(item, dict | list) and item:
                lines.append(f"{prefix}{_yaml_key(key)}:")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}{_yaml_key(key)}: {_yaml_scalar(item)}")
        return lines
    if isinstance(plain, list):
        if not plain:
            return [f"{prefix}[]"]
        lines = []
        for item in plain:
            if isinstance(item, dict | list) and item:
                lines.append(f"{prefix}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_yaml_scalar(item)}")
        return lines
    return [f"{prefix}{_yaml_scalar(plain)}"]


def echo_yaml(value: Any) -> None:
    click.echo("\n".join(_yaml_lines(value)))


def confirm_delete(yes: bool, message: str) -> None:
    if yes:
        return
    click.confirm(message, abort=True)


def build_file_upload(path: Path) -> FileUploadSpec:
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileUploadSpec(
        content=path.read_bytes(),
        filename=path.name,
        content_type=content_type,
    )


def require_identifier(
    filepath: str | None,
    blob_id: str | None,
    artifact_hash: str | None,
) -> None:
    provided = [value for value in (filepath, blob_id, artifact_hash) if value]
    if len(provided) != 1:
        raise click.UsageError(
            "Provide exactly one of -p/--filepath, -b/--blob-id, or "
            "-H/--artifact-hash."
        )
