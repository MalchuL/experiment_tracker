# Experiments

An experiment is one concrete run inside a project. It carries the run metadata and owns the run's scalars, metrics, and experiment artifacts.

## Experiment fields

| Field | Meaning |
|-------|---------|
| `id` | Stable experiment id. |
| `projectId` | Owning project id. |
| `name` | Run name. |
| `description` | Run notes or intent. |
| `status` | Planned, running, complete, or failed. |
| `progress` | `0..100` progress value. |
| `color` | Optional hex color used in plots and run UI. |
| `parentExperimentId` | Optional parent run for DAG and diff views. |
| `features` | Tree of run features, currently used like hyperparameters. |
| `tags` | Optional run tags. |
| `order` | Optional ordering value for project views. |
| `createdAt` | Creation timestamp. |
| `startedAt` / `completedAt` | Status-derived lifecycle timestamps when available. |

## Status and progress

Statuses are:

- `planned`
- `running`
- `failed`
- `complete`

Progress is a `0..100` integer. You may keep it at zero. The progress bar is only useful while a run is `running`; when the status is not running, the UI does not need to show training progress.

SDK example:

```python
from experiment_tracker_sdk import ExperimentStatus

tracker.status(ExperimentStatus.RUNNING)
tracker.progress(25)
tracker.status(ExperimentStatus.COMPLETE)
tracker.progress(100)
```

## Colors

Experiment colors make runs visually distinct. They are especially important on scalar plots, where multiple experiments may share the same chart. Colors must be hex strings such as `#3366cc` or `#3366ccff`.

## Features, hyperparameters, and parent diffs

Features are a tree of named nodes that describe semantic experiment changes.

```python
tracker.features([
    {
        "name": "model",
        "children": [
            {"name": "small-cnn"},
            {"name": "dropout-0.1"},
        ],
    },
    {
        "name": "data",
        "children": [{"name": "mnist"}],
    },
])
```

When an experiment has a parent, the sidebar can show differences from the parent
experiment and let users edit the feature tree. Use this for "what changed in this
run?" information.

Hyperparameters are stored separately as nested JSON and can be logged through
`tracker.log_hparams(...)` or edited from the experiment sidebar. The Compare page
shows baseline-relative added, removed, and changed hyperparameter values.

## Parent experiments and DAG

`parentExperimentId` links experiments into a project DAG. The DAG view uses these relationships to show lineage and can display a limited number of project display metrics on each node.

Parent experiments must belong to the same project. The SDK helper `parent_experiment(...)` resolves by name or id within the current project.

## Data owned by an experiment

An experiment owns:

- [scalars](/docs/domains/scalars), such as loss curves and training progress;
- [metrics](/docs/domains/metrics), such as final accuracy or best validation loss;
- [at-step artifacts](/docs/domains/artifacts#step-artifacts), such as prediction images or text notes;
- [final experiment artifacts](/docs/domains/artifacts#final-experiment-artifacts), such as configs, models, or reports.

Deleting an experiment performs best-effort cleanup in object storage and scalars before deleting the experiment row.

## Related

- [Experiment logging with ExpTracker](/docs/sdk/experiment-logging)
- [Scalars](/docs/domains/scalars)
- [Metrics](/docs/domains/metrics)
- [DAG view](/docs/reference/dag-view)
