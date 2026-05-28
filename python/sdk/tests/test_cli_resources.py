from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from click.testing import CliRunner


@dataclass
class FakeSpec:
    domain: str
    method: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class FakeFactory:
    def __init__(self, domain: str, calls: list[FakeSpec]) -> None:
        self.domain = domain
        self.calls = calls

    def __getattr__(self, method: str) -> Any:
        def _call(*args: Any, **kwargs: Any) -> FakeSpec:
            spec = FakeSpec(self.domain, method, args, kwargs)
            self.calls.append(spec)
            return spec

        return _call


class FakeRegistry:
    def __init__(self, calls: list[FakeSpec]) -> None:
        self.projects = FakeFactory("projects", calls)
        self.teams = FakeFactory("teams", calls)
        self.experiments = FakeFactory("experiments", calls)
        self.metrics = FakeFactory("metrics", calls)
        self.experiment_artifacts = FakeFactory("experiment_artifacts", calls)


class FakeClient:
    def __init__(self) -> None:
        self.requests: list[FakeSpec] = []

    def request(self, spec: FakeSpec) -> Any:
        self.requests.append(spec)
        if spec.method == "get_project_metrics_by_label":
            return _metric_snapshot()
        if spec.method == "download_named_experiment_artifact":
            from experiment_tracker_sdk.client.request_types import FileDownloadResponse

            return FileDownloadResponse(
                content=b"artifact-bytes",
                filename="artifact.bin",
            )
        return {
            "domain": spec.domain,
            "method": spec.method,
            "displayName": "Влад Сорокин",
            "args": list(spec.args),
            "kwargs": _jsonable_kwargs(spec.kwargs),
        }


class FakeAccess:
    def __init__(self) -> None:
        self.calls: list[FakeSpec] = []
        self.request_client = FakeClient()
        self.api_requests_registry = FakeRegistry(self.calls)

    @classmethod
    def instance(cls) -> FakeAccess:
        return fake_access


fake_access = FakeAccess()


def _jsonable_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key == "file":
            out[key] = {
                "filename": value.filename,
                "content": value.content.decode(),
                "content_type": value.content_type,
            }
        else:
            out[key] = value
    return out


def _metric_snapshot() -> Any:
    from experiment_tracker_sdk.client.domain.metrics.dto import (
        MetricsByLabelRowResponse,
        MetricsByLabelSnapshotResponse,
    )

    return MetricsByLabelSnapshotResponse(
        metricNames=["loss", "accuracy"],
        rows=[
            MetricsByLabelRowResponse(
                experimentId="exp-1",
                experimentName="Run 1",
                createdAt=datetime(2026, 5, 26, 12, 0, tzinfo=timezone.utc),
                color="#123456",
                values=[0.25, 0.95],
            )
        ],
        total=1,
        hasNext=False,
    )


def _install_fake_access(monkeypatch) -> FakeAccess:
    global fake_access
    fake_access = FakeAccess()
    from experiment_tracker_sdk.console.domain_cli import common

    monkeypatch.setattr(common, "ExpTrackerApiAccess", FakeAccess)
    return fake_access


def test_resource_groups_are_registered() -> None:
    from experiment_tracker_sdk.console.commands import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "project" in result.output
    assert "team" in result.output
    assert "experiment" in result.output
    assert "metric" in result.output
    assert "experiment-artifact" in result.output


def test_project_team_experiment_mutation_commands(monkeypatch) -> None:
    from experiment_tracker_sdk.console.commands import cli

    access = _install_fake_access(monkeypatch)
    runner = CliRunner()

    commands = [
        ["project", "create", "-n", "MNIST", "-d", "Short", "-t", "team-1"],
        ["project", "update", "project-1", "-n", "MNIST Legacy"],
        ["project", "delete", "project-1", "-y"],
        ["team", "create", "-n", "Research", "-d", "Core"],
        ["team", "update", "team-1", "-n", "Research 2"],
        ["team", "delete", "team-1", "-y"],
        ["experiment", "create", "-p", "project-1", "-n", "Run 1", "-g", "gpu"],
        ["experiment", "update", "exp-1", "-s", "running", "-r", "25"],
        ["experiment", "delete", "exp-1", "-y"],
    ]
    outputs = []
    for command in commands:
        result = runner.invoke(cli, command)
        assert result.exit_code == 0, result.output
        outputs.append(result.output)

    for output in outputs:
        assert "domain:" in output
        assert '"domain"' not in output

    calls = [
        (call.domain, call.method, call.args, call.kwargs) for call in access.calls
    ]
    assert calls[0][0:2] == ("projects", "create_project")
    assert calls[0][3]["name"] == "MNIST"
    assert calls[0][3]["description"] == "Short"
    assert calls[0][3]["team_id"] == "team-1"
    assert calls[1][0:2] == ("projects", "update_project")
    assert calls[1][3]["project_id"] == "project-1"
    assert calls[2][0:2] == ("projects", "delete_project")
    assert calls[3][0:2] == ("teams", "create_team")
    assert calls[4][0:2] == ("teams", "update_team")
    assert calls[5][0:2] == ("teams", "delete_team")
    assert calls[6][0:2] == ("experiments", "create_experiment")
    assert calls[6][3]["project_id"] == "project-1"
    assert calls[6][3]["tags"] == ["gpu"]
    assert calls[7][0:2] == ("experiments", "update_experiment")
    assert calls[7][3]["progress"] == 25
    assert calls[8][0:2] == ("experiments", "delete_experiment")


def test_metric_single_upsert(monkeypatch) -> None:
    from experiment_tracker_sdk.console.commands import cli

    access = _install_fake_access(monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["metric", "upsert", "-e", "exp-1", "-a", "train", "-n", "loss", "-v", "0.5"],
    )

    assert result.exit_code == 0, result.output
    assert 'domain: "metrics"' in result.output
    assert 'displayName: "Влад Сорокин"' in result.output
    assert "\\u0412" not in result.output
    assert '"domain"' not in result.output
    call = access.calls[0]
    assert call.domain == "metrics"
    assert call.method == "upsert_metric"
    assert call.kwargs == {
        "experiment_id": "exp-1",
        "name": "loss",
        "value": 0.5,
        "label": "train",
    }


def test_metric_interactive_upsert_validates_and_stops(monkeypatch) -> None:
    from experiment_tracker_sdk.console.commands import cli

    access = _install_fake_access(monkeypatch)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["metric", "upsert", "-e", "exp-1", "-a", "train", "-i"],
        input="bad-row\nvalidation loss 0.75\n\n\n",
    )

    assert result.exit_code == 0, result.output
    assert "Invalid metric row" in result.stderr
    assert len(access.calls) == 1
    assert access.calls[0].kwargs == {
        "experiment_id": "exp-1",
        "name": "validation loss",
        "value": 0.75,
        "label": "train",
    }


def test_metric_dump_formats(monkeypatch) -> None:
    from experiment_tracker_sdk.console.commands import cli

    _install_fake_access(monkeypatch)
    runner = CliRunner()

    table = runner.invoke(cli, ["metric", "dump", "-p", "project-1", "-a", "train"])
    json_result = runner.invoke(
        cli,
        ["metric", "dump", "-p", "project-1", "-a", "train", "-f", "json"],
    )
    csv_result = runner.invoke(
        cli,
        ["metric", "dump", "-p", "project-1", "-a", "train", "-f", "csv"],
    )
    md_result = runner.invoke(
        cli,
        ["metric", "dump", "-p", "project-1", "-a", "train", "-f", "md"],
    )

    assert table.exit_code == 0
    assert "experimentId" in table.output
    assert "loss" in table.output
    assert json_result.exit_code == 0
    assert '"metricNames": [' in json_result.output
    assert csv_result.exit_code == 0
    assert csv_result.output.splitlines()[0] == (
        "experimentId,experimentName,createdAt,color,loss,accuracy"
    )
    assert md_result.exit_code == 0
    header = "| experimentId | experimentName | createdAt | color | loss | accuracy |"
    assert header in md_result.output


def test_experiment_artifact_upsert_download_delete(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from experiment_tracker_sdk.console.commands import cli

    access = _install_fake_access(monkeypatch)
    runner = CliRunner()
    source = tmp_path / "model.bin"
    source.write_bytes(b"payload")
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()

    upsert = runner.invoke(
        cli,
        [
            "experiment-artifact",
            "upsert",
            "-e",
            "exp-1",
            "-F",
            str(source),
            "-p",
            "checkpoints/model.bin",
            "-n",
            "best",
        ],
    )
    download = runner.invoke(
        cli,
        [
            "experiment-artifact",
            "download",
            "-e",
            "exp-1",
            "-p",
            "checkpoints/model.bin",
            "-O",
            str(output_dir),
        ],
    )
    delete = runner.invoke(
        cli,
        [
            "experiment-artifact",
            "delete",
            "-e",
            "exp-1",
            "-p",
            "checkpoints/model.bin",
            "-y",
        ],
    )

    assert upsert.exit_code == 0, upsert.output
    assert download.exit_code == 0, download.output
    assert delete.exit_code == 0, delete.output
    assert 'domain: "experiment_artifacts"' in upsert.output
    assert '"domain"' not in upsert.output
    assert 'domain: "experiment_artifacts"' in delete.output
    assert '"domain"' not in delete.output
    assert (output_dir / "artifact.bin").read_bytes() == b"artifact-bytes"
    assert access.calls[0].method == "upsert_named_experiment_artifact"
    assert access.calls[0].kwargs["file"].content == b"payload"
    assert access.calls[1].method == "download_named_experiment_artifact"
    assert access.calls[2].method == "delete_named_experiment_artifacts"


def test_experiment_artifact_requires_one_identifier(monkeypatch) -> None:
    from experiment_tracker_sdk.console.commands import cli

    _install_fake_access(monkeypatch)
    runner = CliRunner()

    result = runner.invoke(cli, ["experiment-artifact", "get", "-e", "exp-1"])

    assert result.exit_code != 0
    assert "Provide exactly one" in result.output
