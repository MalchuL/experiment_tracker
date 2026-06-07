# Experiment logging with ExpTracker

Use `ExpTracker` inside training scripts when you want a small TensorBoard-like API that writes directly to Experiment Tracker.

The `examples/training` example is the best end-to-end reference. It initializes a tracker, updates experiment metadata, logs scalars and artifacts during the run, writes final comparison metrics, and marks the experiment complete or failed.

## Initialize a run

```python
from experiment_tracker_sdk import ExperimentStatus, ExpTracker, InitParams

tracker = ExpTracker.init(
    project="SDK Training",
    experiment="SDK Training Run",
    team=None,
    init_params=InitParams(
        create_team_if_not_exists=False,
        create_project_if_not_exists=False,
        create_experiment_if_not_exists=True,
    ),
)
```

`project`, `experiment`, and `team` can be names or ids. If `init_params` is omitted, missing experiments are created by default, while projects and teams must already exist.

After initialization, call `get_project_settings()` to fetch the current project's runtime settings as a plain dictionary:

```python
settings = tracker.get_project_settings()
batch_size = settings.get("batch_size", 32)
```

For examples and local smoke tests, it is common to create everything on demand:

```python
tracker = ExpTracker.init(
    project="SDK Training",
    experiment="SDK Training Run",
    team=None,
    init_params=InitParams(
        create_team_if_not_exists=True,
        create_project_if_not_exists=True,
        create_experiment_if_not_exists=True,
    ),
)
```

:::warning
For real training jobs, confirm the target project, team, backend URL, and token before starting long runs. Creating projects automatically is convenient for examples but can send data to the wrong workspace if local config is stale.
:::

## Lifecycle pattern

Wrap the training body so failures mark the experiment as failed and `close()` always flushes pending data.

```python
import logging

from experiment_tracker_sdk import ExperimentStatus, ExpTracker, InitParams

logger = logging.getLogger(__name__)
tracker: ExpTracker | None = None

try:
    tracker = ExpTracker.init(
        project="SDK Training",
        experiment="Baseline",
        init_params=InitParams(create_experiment_if_not_exists=True),
    )

    tracker.features([
        {
            "name": "training",
            "children": [
                {"name": "optimizer-adam"},
                {"name": "dataset-v1"},
            ],
        }
    ])
    tracker.tags("baseline", "demo")
    tracker.description("Baseline run from the SDK docs")
    tracker.status(ExperimentStatus.RUNNING)
    tracker.progress(0)

    for step in range(1, 101):
        loss = 1.0 / step
        accuracy = step / 100
        tracker.add_scalar("loss", loss, global_step=step)
        tracker.add_scalar("accuracy", accuracy, global_step=step)
        tracker.progress(step)

    tracker.add_metric("loss", loss, label="final")
    tracker.add_metric("accuracy", accuracy, label="final")
    tracker.flush()

    tracker.status(ExperimentStatus.COMPLETE)
    tracker.progress(100)
except Exception:
    if tracker is not None:
        try:
            tracker.status(ExperimentStatus.FAILED)
            tracker.flush()
        except Exception:
            logger.exception("failed_to_mark_experiment_failed")
    raise
finally:
    if tracker is not None:
        tracker.close()
```

## Scalars and metrics

`add_scalar` writes a time-series value for a specific step. Use it for curves such as training loss, validation accuracy, learning rate, or any value that changes over time.

```python
tracker.add_scalar("train/loss", loss, global_step=step)
tracker.add_scalar("val/accuracy", accuracy, global_step=epoch)
```

`add_metric` creates or updates a metric row for the experiment. Use it for final values and comparison tables.

```python
tracker.add_metric("loss", final_loss, label="final")
tracker.add_metric("accuracy", final_accuracy, label="final")
tracker.add_metric("e+3", 1000.0, label="power")
```

Non-finite scalar and metric values are skipped. For example, `float("nan")` is not logged.

## Step artifacts

Step artifacts are tied to `global_step` and appear alongside training progress. Use them for predictions, images, generated samples, notes, and other outputs that belong to a point in time.

```python
tracker.add_text(
    "training_note",
    f"step={step} loss={loss:.4f} accuracy={accuracy:.4f}",
    global_step=step,
)
```

`add_image` accepts PIL images and numpy arrays in HW or HWC layout when the optional image dependencies are available.

```python
import numpy as np

image = np.random.randint(0, 256, size=(256, 256, 3), dtype=np.uint8)
tracker.add_image("generated", image, global_step=step)
```

## Final artifacts

Final artifacts are named experiment artifacts without a step. Use them for configs, checkpoints, package snapshots, final reports, and exports.

```python
tracker.log_final_artifact(
    "run_config",
    "learning_rate: 0.001\nbatch_size: 64\n",
    stored_filepath="final/config.yaml",
    default_content_type="application/x-yaml",
)

tracker.log_final_text("python_packages", installed_packages)
tracker.log_final_json("training_summary", {"loss": final_loss, "accuracy": final_accuracy})
tracker.log_final_yaml("run_config_helper", {"run": {"epochs": 10}})
tracker.log_final_image("final_prediction_grid", image)
```

`log_final_artifact` is the generic helper. It accepts bytes, text, a local file path, or a readable file-like object. The typed helpers set common content types and default extensions for text, JSON, YAML, and images.

## Metadata helpers

`ExpTracker` can update experiment metadata while the run is active:

```python
tracker.name("New display name")
tracker.description("Run description")
tracker.tags("baseline", "augmented")
tracker.color("#3366cc")
tracker.progress(42)
tracker.status(ExperimentStatus.RUNNING)
tracker.parent_experiment("Previous baseline")
tracker.features([
    {"name": "data", "children": [{"name": "mnist"}]},
    {"name": "model", "children": [{"name": "small-cnn"}]},
])
tracker.log_hparams({
    "optimizer": {"name": "adamw", "lr": 3e-4},
    "training": {"batch_size": 32, "epochs": 50},
})
```

`progress` accepts `0..100` integers or `0..1` floats. `parent_experiment` resolves by name or id inside the current project.

`features` describe semantic changes and research ideas. `log_hparams` stores the
configurable training values used by the run. Each `log_hparams` call fully replaces
the experiment's previous hyperparameter document.

## Run the repository example

```bash
cd examples/training
uv sync
uv add ../../python/sdk
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
uv run experiment-tracker run --project mnist train.py -- --epochs 100 --max-train-batches 100 --max-val-batches 100
```

The example logs dense scalar series, sparse scalar series, final metrics, text and image step artifacts, and several named final artifacts.

## ExpTracker method reference

Use this section as the detailed reference for the high-level `ExpTracker` API. In normal training code, create a tracker with `ExpTracker.init(...)`; the direct constructor is used internally after project and experiment resolution.

### `ExpTracker.init(...)`

```python
tracker = ExpTracker.init(
    project="SDK Training",
    experiment="SDK Training Run",
    team=None,
    init_params=InitParams(create_experiment_if_not_exists=True),
)
```

Initializes a tracker bound to one experiment.

Arguments:

| Argument | Meaning |
|----------|---------|
| `project` | Project name or id. |
| `experiment` | Experiment name or id inside the project. |
| `team` | Optional team name or id for team-owned projects. |
| `init_params` | Optional creation/reuse policy for team, project, and experiment resolution. |

Default behavior when `init_params` is omitted:

- missing experiment is created;
- missing project is not created;
- missing team is not created.

Use explicit `InitParams` for examples, notebooks, and automation where creating missing resources is expected.

---

### `get_project_settings()`

```python
settings = tracker.get_project_settings()
```

Fetches the current project's settings from `GET /projects/{project_id}/settings/map` and returns them as a `dict` keyed by setting name.

Use this for runtime configuration values that should be controlled at the project level, such as dataset identifiers, feature flags, or external resource names.

---

### `add_scalar(...)`

```python
tracker.add_scalar("train/loss", loss, global_step=step)
```

Logs one finite numeric scalar point at a step.

Arguments:

| Argument | Meaning |
|----------|---------|
| `tag` | Scalar series name. |
| `scalar_value` | Numeric value. Must be finite. |
| `global_step` | Step index. Defaults to `0`. |
| `walltime` | Kept for TensorBoard-like API parity; currently not used. |

`NaN`, `Inf`, `-Inf`, non-numeric values, and null-like values are skipped with an SDK warning.

---

### `add_scalars(...)`

```python
tracker.add_scalars(
    "train/",
    {"loss": loss, "accuracy": accuracy},
    global_step=step,
)
```

Logs multiple scalar values at the same step by calling `add_scalar` for each entry.

Arguments:

| Argument | Meaning |
|----------|---------|
| `main_tag` | Prefix prepended to each scalar key. |
| `tag_scalar_dict` | Mapping of suffix to numeric value. |
| `global_step` | Step index. |
| `walltime` | Kept for API parity; currently not used. |

The SDK concatenates `main_tag + tag` directly. Include separators yourself, for example `main_tag="train/"`.

---

### `add_metric(...)`

```python
tracker.add_metric("accuracy", final_accuracy, label="final")
```

Creates or updates one metric row for the current experiment.

Arguments:

| Argument | Meaning |
|----------|---------|
| `name` | Metric name. |
| `value` | Finite numeric value. |
| `label` | Optional label for separating incomparable values. |
| `walltime` | Kept for API parity; currently not used. |

Metrics are not time series. Reusing the same `(experiment, name, label)` overwrites the previous metric value.

---

### `add_image(...)`

```python
tracker.add_image("generated", image, global_step=step)
```

Uploads an image as an at-step artifact. It appears with logged objects on the scalars page.

Arguments:

| Argument | Meaning |
|----------|---------|
| `tag` | Artifact name. |
| `img` | PIL image or numpy array in HW/HWC layout. |
| `global_step` | Step associated with the image. |
| `walltime` | Kept for API parity; currently not used. |

The SDK converts supported inputs to PNG and logs artifact metadata with type `image`.

---

### `add_text(...)`

```python
tracker.add_text("training_note", "loss improved after warmup", global_step=step)
```

Uploads text as an at-step artifact.

Arguments:

| Argument | Meaning |
|----------|---------|
| `tag` | Artifact name. |
| `text_string` | Text content. |
| `global_step` | Step associated with the text. |
| `walltime` | Kept for API parity; currently not used. |

Text is uploaded as UTF-8 content and logged with artifact type `text`.

---

### `log_final_artifact(...)`

```python
tracker.log_final_artifact(
    "model",
    model_bytes,
    stored_filepath="final/model.pt",
    default_content_type="application/octet-stream",
)
```

Uploads a named final experiment artifact without a step. Use this generic method for checkpoints, exports, configs, and files not covered by a typed helper.

Arguments:

| Argument | Meaning |
|----------|---------|
| `tag` | Display name stored with the artifact. |
| `content` | Bytes, text, local file path, or readable file-like object. |
| `stored_filepath` | Relative artifact path. If omitted, SDK derives one from `tag`. |
| `default_content_type` | MIME type fallback. |
| `default_extension` | Extension used when deriving a default path/name. |

The stable key is `stored_filepath`. Uploading another final artifact with the same path replaces the previous file and metadata.

---

### `log_final_image(...)`

```python
tracker.log_final_image(
    "final_prediction_grid",
    image,
    stored_filepath="final/predictions.png",
)
```

Uploads a named final image artifact. It accepts image bytes, an existing image path, a readable file-like object, a PIL image, or a numpy array.

Non-file image data is converted to PNG. The default content type is `image/png`.

---

### `log_final_text(...)`

```python
tracker.log_final_text("python_packages", installed_packages)
```

Uploads a named final text artifact. It accepts text, bytes, a local text path, or a readable file-like object.

The default content type is `text/plain`, and the default extension is `.txt`.

---

### `log_final_json(...)`

```python
tracker.log_final_json(
    "training_summary",
    {"loss": final_loss, "accuracy": final_accuracy},
    stored_filepath="final/summary.json",
)
```

Uploads a named final JSON artifact.

Arguments:

| Argument | Meaning |
|----------|---------|
| `tag` | Display name. |
| `content` | JSON text, bytes, local JSON path, file-like object, or mapping/list payload. |
| `stored_filepath` | Optional relative artifact path. |
| `indent` | Indentation for structured payload serialization. Defaults to `2`. |

Structured mappings/lists are serialized with `json.dumps`.

---

### `log_final_yaml(...)`

```python
tracker.log_final_yaml(
    "run_config",
    {"run": {"epochs": 10, "lr": 0.001}},
)
```

Uploads a named final YAML artifact.

Arguments:

| Argument | Meaning |
|----------|---------|
| `tag` | Display name. |
| `content` | YAML text, bytes, local YAML path, file-like object, or mapping/list payload. |
| `stored_filepath` | Optional relative artifact path. |

Structured mappings/lists are serialized with the SDK's lightweight YAML emitter. The default content type is `application/x-yaml`.

---

### `log_snapshot(...)`

```python
result = tracker.log_snapshot(".")

# Pin manifest paths to a known project root.
result = tracker.log_snapshot(
    "src",
    root="/absolute/path/to/project",
)
```

Uploads a file snapshot for the current experiment. Use this for source code, lightweight configs, and other files that should be comparable between runs.

Arguments:

| Argument | Meaning |
|----------|---------|
| `path` | File, directory, or iterable of files/directories to scan. Defaults to `"."`. |
| `root` | Optional absolute directory used for manifest-relative paths. When omitted, the SDK discovers the root from ignore files. |
| `ignore_file` | Ignore file names to apply. Defaults to `.gitignore` and `.exp_tracker_ignore`. |
| `max_file_size` | Maximum file size in bytes. Omit to use `EXP_TRACKER_SNAPSHOT_MAX_FILE_SIZE`; pass `None` or `-1` to disable. |

When `root` is `None`, the SDK searches upward from the scanned path for `.gitignore` or `.exp_tracker_ignore` and uses the nearest matching directory as the snapshot root. If no ignore file is found, the scanned path or common parent is used. When `root` is provided, it must be an absolute path to an existing directory, and every scanned path must be inside it.

The default snapshot size limit is 5 MiB per file. Skipped files are counted in the result, and `experiment-tracker check-files --show-skipped` reports reasons: `ignored`, `too_large`, or `not_file`. To preview a pinned root, pass `--root /absolute/path/to/project` to `check-files`.

:::warning
Snapshot storage is currently intended for small code/config snapshots, not large repository archives or dataset-like trees. The current implementation does not store very large snapshots efficiently and is practically limited to about 250k files per snapshot.
:::

---

### `progress(...)`

```python
tracker.progress(42)
tracker.progress(0.42)
```

Updates experiment progress.

Accepted values:

- integer `0..100`;
- float `0..1`, converted to percent.

Values outside the range are clamped. Progress is most useful while status is `RUNNING`.

---

### `status(...)`

```python
tracker.status(ExperimentStatus.RUNNING)
tracker.status(ExperimentStatus.COMPLETE)
```

Updates experiment status. Supported statuses are:

- `ExperimentStatus.PLANNED`
- `ExperimentStatus.RUNNING`
- `ExperimentStatus.COMPLETE`
- `ExperimentStatus.FAILED`

Use `FAILED` in exception handling so interrupted or crashed runs are visible in the UI.

---

### `tags(...)`

```python
tracker.tags("baseline", "augmentation-v2")
```

Replaces the experiment tag list with the provided strings. Calling `tags(...)` again writes a new full tag list.

---

### `color(...)`

```python
tracker.color("#3366cc")
```

Updates the experiment display color. Use colors to make runs easier to distinguish in scalar plots and experiment views.

The backend accepts hex colors such as `#3366cc` or `#3366ccff`.

---

### `description(...)`

```python
tracker.description("Baseline with the new dataset split.")
```

Updates the experiment description.

Use this for short run intent, context, or notes that should be visible with the experiment.

---

### `features(...)`

```python
tracker.features([
    {"name": "optimizer", "children": [{"name": "adam"}]},
    {"name": "lr", "children": [{"name": "0.001"}]},
])
```

Updates the experiment feature tree. Use features for semantic changes, ablations,
new mechanisms, and "what changed" information rather than configurable training
values.

When an experiment has a parent, the sidebar can show feature differences from that parent.

---

### `log_hparams(...)`

```python
tracker.log_hparams({
    "optimizer": {
        "name": "adamw",
        "lr": 0.001,
    },
    "training": {
        "batch_size": 64,
        "seed": 42,
    },
})
```

Validates and stores a nested hyperparameter JSON object. Repeated calls fully replace
the previous document; they do not deep-merge it. Common values such as `Path`, `Enum`,
`date`, `datetime`, and NumPy scalar values are converted when safe. Unsupported values
raise `HparamsSerializationError` with the failing parameter path.

---

### `name(...)`

```python
tracker.name("Baseline v2")
```

Updates the experiment display name.

---

### `parent_experiment(...)`

```python
tracker.parent_experiment("Previous baseline")
tracker.parent_experiment("9a3f0c7d-...")
```

Sets the current experiment's parent by name or id. The SDK searches experiments in the current project and raises `ExpTrackerAPIError` if it cannot find a match.

The parent must belong to the same project. Parent links drive the DAG view and parent-diff sidebar.

---

### `flush()`

```python
tracker.flush()
```

Flushes queued scalar logging and pending HTTP requests. Call it before marking important lifecycle transitions or before a long process exits.

`close()` also flushes, so most scripts should still call `close()` in a `finally` block.

---

### `close()`

```python
tracker.close()
```

Flushes scalar logging, flushes pending HTTP requests, and closes the underlying request client.

Always call `close()` when the script is done. The usual pattern is:

```python
finally:
    if tracker is not None:
        tracker.close()
```

---

### Context manager

```python
with ExpTracker.init(project="SDK Training", experiment="Run") as tracker:
    tracker.description("Updated in batched metadata mode")
    tracker.tags("baseline")
```

`ExpTracker` implements `__enter__` and `__exit__`. The context manager enters the underlying experiment metadata batching mode, so multiple metadata assignments can be grouped before the context exits.

This is for experiment metadata updates. It does not replace `close()` for long-lived training scripts that log scalars and artifacts.

## Unsupported ExpTracker methods

These methods exist for TensorBoard-like API compatibility, but they are not implemented today. Calling them logs a warning and does not store data.

### `add_histogram(...)`

Not supported. The method logs a warning and does not store histogram data.

---

### `add_audio(...)`

Not supported. The method logs a warning and does not upload or store audio data.

---

### `add_figure(...)`

Not supported. The method logs a warning and does not convert or upload matplotlib figures.

---

### `add_mesh(...)`

Not supported. The method logs a warning and does not upload mesh or point-cloud payloads.

---

### `add_video(...)`

Not supported. The method logs a warning and does not upload or store video data.

---

### `add_embedding(...)`

Not supported. The method logs a warning and does not store embedding projector data.
