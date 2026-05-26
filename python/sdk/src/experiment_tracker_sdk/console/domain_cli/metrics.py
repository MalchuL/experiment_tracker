"""Metric resource CLI commands."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Sequence
from io import StringIO
from typing import Any, cast

import click

from experiment_tracker_sdk.client.domain.metrics.dto import (
    MetricsByLabelSnapshotResponse,
)

from .common import api, confirm_delete, echo_yaml, model_to_plain


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _render_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    normalized = [[_format_cell(value) for value in row] for row in rows]
    widths = [
        max([len(header), *(len(row[index]) for row in normalized)])
        for index, header in enumerate(headers)
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in normalized
    )
    return "\n".join(lines)


def _render_markdown(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    normalized = [[_format_cell(value) for value in row] for row in rows]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in normalized)
    return "\n".join(lines)


def _metric_snapshot_table(
    snapshot: MetricsByLabelSnapshotResponse,
) -> tuple[list[str], list[list[Any]]]:
    headers = ["experimentId", "experimentName", "createdAt", "color"]
    headers.extend(snapshot.metricNames)
    rows: list[list[Any]] = []
    for row in snapshot.rows:
        rows.append(
            [
                row.experimentId,
                row.experimentName,
                row.createdAt.isoformat(),
                row.color,
                *row.values,
            ]
        )
    return headers, rows


def _metric_snapshot_records(
    snapshot: MetricsByLabelSnapshotResponse,
) -> list[dict[str, Any]]:
    headers, rows = _metric_snapshot_table(snapshot)
    return [dict(zip(headers, row, strict=True)) for row in rows]


def _echo_metric_dump(
    snapshot: MetricsByLabelSnapshotResponse,
    output_format: str,
) -> None:
    headers, rows = _metric_snapshot_table(snapshot)
    if output_format == "json":
        click.echo(
            json.dumps(
                model_to_plain(
                    {
                        "metricNames": snapshot.metricNames,
                        "rows": _metric_snapshot_records(snapshot),
                        "hasNext": snapshot.hasNext,
                        "total": snapshot.total,
                    }
                ),
                indent=2,
                default=str,
                ensure_ascii=False,
            )
        )
        return
    if output_format == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerows(rows)
        click.echo(buffer.getvalue().rstrip("\r\n"))
        return
    if output_format == "md":
        click.echo(_render_markdown(headers, rows))
        return
    click.echo(_render_table(headers, rows))


def _parse_metric_line(line: str) -> tuple[str, float]:
    name, separator, raw_value = line.rpartition(" ")
    if separator == "" or name.strip() == "":
        raise click.BadParameter("expected '<metric name> <value>'")
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise click.BadParameter("value must be a float") from exc
    return name.strip(), value


def _iter_interactive_metrics() -> Iterable[tuple[str, float]]:
    blank_count = 0
    while True:
        line = click.prompt("metric", default="", show_default=False)
        if line == "":
            blank_count += 1
            if blank_count >= 2:
                return
            continue
        blank_count = 0
        try:
            yield _parse_metric_line(line)
        except click.BadParameter as exc:
            click.echo(f"Invalid metric row: {exc.message}", err=True)


@click.group("metric", short_help="Manage metrics")
def metric_group() -> None:
    """Manage metrics."""


@metric_group.command("list")
@click.option("-e", "--experiment-id", default=None)
@click.option("-p", "--project-id", default=None)
@click.option("-l", "--limit", type=int, default=None)
@click.option("-o", "--offset", type=int, default=None)
def metric_list_command(
    experiment_id: str | None,
    project_id: str | None,
    limit: int | None,
    offset: int | None,
) -> None:
    if bool(experiment_id) == bool(project_id):
        raise click.UsageError(
            "Provide exactly one of -e/--experiment-id or -p/--project-id."
        )
    client, registry = api()
    spec = (
        registry.metrics.get_experiment_metrics(experiment_id, limit, offset)
        if experiment_id is not None
        else registry.metrics.get_project_metrics(project_id, limit, offset)
    )
    echo_yaml(client.request(spec))


@metric_group.command("get")
@click.option("-e", "--experiment-id", required=True)
@click.option("-n", "--name", required=True)
@click.option("-a", "--label", default=None)
def metric_get_command(
    experiment_id: str,
    name: str,
    label: str | None,
) -> None:
    client, registry = api()
    echo_yaml(
        client.request(
            registry.metrics.get_metric(
                experiment_id=experiment_id,
                name=name,
                label=label,
            )
        )
    )


@metric_group.command("upsert")
@click.option("-e", "--experiment-id", required=True)
@click.option("-a", "--label", required=True)
@click.option("-n", "--name", default=None)
@click.option("-v", "--value", type=float, default=None)
@click.option("-i", "--interactive", is_flag=True)
def metric_upsert_command(
    experiment_id: str,
    label: str,
    name: str | None,
    value: float | None,
    interactive: bool,
) -> None:
    client, registry = api()
    if interactive:
        for metric_name, metric_value in _iter_interactive_metrics():
            response = client.request(
                registry.metrics.upsert_metric(
                    experiment_id=experiment_id,
                    name=metric_name,
                    value=metric_value,
                    label=label,
                )
            )
            echo_yaml(response)
        return
    if name is None or value is None:
        raise click.UsageError(
            "Provide -n/--name and -v/--value, or use -i/--interactive."
        )
    echo_yaml(
        client.request(
            registry.metrics.upsert_metric(
                experiment_id=experiment_id,
                name=name,
                value=value,
                label=label,
            )
        )
    )


@metric_group.command("delete")
@click.argument("metric_id")
@click.option("-y", "--yes", is_flag=True)
def metric_delete_command(metric_id: str, yes: bool) -> None:
    confirm_delete(yes, f"Delete metric {metric_id}?")
    client, registry = api()
    echo_yaml(client.request(registry.metrics.delete_metric(metric_id)))


@metric_group.command("dump")
@click.option("-p", "--project-id", required=True)
@click.option("-a", "--label", required=True)
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv", "md"]),
    default="table",
)
@click.option("-l", "--limit", type=int, default=None)
@click.option("-o", "--offset", type=int, default=None)
def metric_dump_command(
    project_id: str,
    label: str,
    output_format: str,
    limit: int | None,
    offset: int | None,
) -> None:
    client, registry = api()
    snapshot = cast(
        MetricsByLabelSnapshotResponse,
        client.request(
            registry.metrics.get_project_metrics_by_label(
                project_id=project_id,
                label=label,
                limit=limit,
                offset=offset,
            )
        ),
    )
    _echo_metric_dump(snapshot, output_format)
