import json
import os
import subprocess
from pathlib import Path

import pytest

from experiment_tracker_sdk import ExpTracker

from conftest import call, eventually


def test_sdk_initialization_flush_close_and_hparams(api, project, sdk_config):
    """Read back SDK scalars and nested hparams, including scalars flushed on close."""
    tracker = ExpTracker.init(project=project["id"], experiment="SDK training")
    eid = str(tracker.experiment_id)
    try:
        for step in range(12):
            tracker.add_scalar("train/loss", 12 - step, step)
            if step % 3 == 0:
                tracker.add_scalar("validation/accuracy", step / 12, step)
        tracker.log_hparams({"lr": 0.01, "model": {"layers": [16, 8]}, "enabled": True})
        tracker.flush()
        read = eventually(
            lambda: call(api, "GET", f"scalars/get/{eid}"),
            lambda data: (
                bool(data["data"])
                and len(data["data"][0]["scalars"].get("train/loss", {}).get("x", []))
                == 12
            ),
        )
        assert read["data"][0]["scalars"]["train/loss"] == {
            "x": list(range(12)),
            "y": list(range(12, 0, -1)),
        }
        assert read["data"][0]["scalars"]["validation/accuracy"]["x"] == [0, 3, 6, 9]
        assert call(api, "GET", f"experiments/{eid}/hparams")["hparams"]["model"] == {
            "layers": [16, 8]
        }
        tracker.add_scalar("train/loss", 0.125, 12)
    finally:
        tracker.close()
    read = eventually(
        lambda: call(api, "GET", f"scalars/get/{eid}"),
        lambda data: len(data["data"][0]["scalars"]["train/loss"]["x"]) == 13,
    )
    assert read["data"][0]["scalars"]["train/loss"]["y"][-1] == 0.125


def test_scalars_experiment_pagination_sampling_tags_and_metric_upsert(
    api, project, experiment
):
    """Paginate and sample tagged scalar runs, then replace a metric by its key."""
    pid, eid = project["id"], experiment["id"]
    second = call(api, "POST", "experiments", json={"projectId": pid, "name": "Second"})
    for current in (eid, second["id"]):
        call(
            api,
            "POST",
            f"scalars/log_batch/{current}",
            json={
                "scalars": [
                    {"step": step, "scalars": {"loss": float(step)}, "tags": ["train"]}
                    for step in range(20)
                ]
            },
        )
    eventually(
        lambda: call(api, "GET", f"scalars/get/project/{pid}"),
        lambda data: len(data["data"]) == 2,
    )
    pages = [
        call(
            api,
            "GET",
            f"scalars/get/project/{pid}",
            params={"limit": 1, "offset": offset, "max_points": 5, "return_tags": True},
        )
        for offset in (0, 1)
    ]
    assert {page["data"][0]["experiment_id"] for page in pages} == {eid, second["id"]}
    for page in pages:
        series = page["data"][0]["scalars"]["loss"]
        assert 1 <= len(series["x"]) <= 5
        assert series["x"] == sorted(series["x"])
        assert series["y"] == [float(step) for step in series["x"]]
        assert any("train" in row["tags"] for row in page["data"][0]["tags"])
    names = call(api, "GET", f"scalars/names/project/{pid}")
    assert "loss" in json.dumps(names)
    last = call(
        api,
        "POST",
        f"scalars/last_logged/{pid}",
        json={"experiment_ids": [eid, second["id"]]},
    )
    assert {row["experiment_id"] for row in last["data"]} == {eid, second["id"]}
    first = call(
        api,
        "POST",
        "metrics",
        json={"experimentId": eid, "name": "accuracy", "value": 0.5},
    )
    replacement = call(
        api,
        "POST",
        "metrics",
        json={"experimentId": eid, "name": "accuracy", "value": 0.75, "label": ""},
    )
    assert first["id"] == replacement["id"]
    metric = call(
        api, "GET", "metrics/by-key", params={"experimentId": eid, "name": "accuracy"}
    )
    assert metric["value"] == 0.75 and metric["label"] is None
    assert call(api, "GET", f"experiments/{eid}/metrics")["total"] == 1


@pytest.mark.parametrize(
    "params",
    [
        {"max_points": 0},
        {"offset": -1},
        {"sampling": "unknown"},
        {"columns_per_query": 0},
    ],
)
def test_invalid_scalar_queries(api, experiment, params):
    """Reject invalid sampling, pagination, and column-query parameters."""
    call(api, "GET", f"scalars/get/{experiment['id']}", status=422, params=params)


@pytest.mark.parametrize("fails", [False, True], ids=["completed", "failed"])
def test_cli_training_and_resource_readback(api, project, sdk_config, tmp_path, fails):
    """Forward CLI training arguments and persist scalars and success or failure status."""
    script = tmp_path / "train.py"
    script.write_text(
        "import sys\nfrom experiment_tracker_sdk import ExpTracker\nassert sys.argv[1:] == ['--epochs', '2']\nt = ExpTracker.init(project="
        + repr(project["id"])
        + ", experiment='CLI run')\nt.add_scalar('cli/loss', 0.5, 1)\nt.flush()\n"
        + ("raise RuntimeError('intentional training failure')\n" if fails else "")
    )
    executable = str(Path(os.sys.executable).parent / "experiment-tracker")
    result = subprocess.run(
        [
            executable,
            "run",
            str(script),
            "--project",
            project["id"],
            "--experiment",
            "CLI run",
            "--",
            "--epochs",
            "2",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert (result.returncode != 0) == fails, result.stdout + result.stderr
    rows = call(api, "GET", f"projects/{project['id']}/experiments")["data"]
    assert len(rows) == 1, rows
    assert rows[0]["status"] == ("failed" if fails else "complete")
    data = eventually(
        lambda: call(api, "GET", f"scalars/get/{rows[0]['id']}"),
        lambda data: bool(data["data"]),
    )
    assert data["data"][0]["scalars"]["cli/loss"]["y"] == [0.5]
    result = subprocess.run(
        [executable, "project", "get", project["id"]],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0 and project["id"] in result.stdout, (
        result.stdout + result.stderr
    )
