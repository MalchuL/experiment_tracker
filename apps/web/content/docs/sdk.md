# SDK

The Python SDK is the recommended way to send training runs, metrics, scalar time series, and artifacts to Experiment Tracker from scripts.

Most experiment code should use the high-level `ExpTracker` class. Use the CLI for setup, quick checks, script launching, and one-off resource operations. Use the low-level client APIs when you need explicit request control or are building tooling around the tracker.

## Install

Install the SDK from the repository package:

```bash
pip install "experiment-tracker-sdk @ git+https://github.com/MalchuL/experiment_tracker.git@main#subdirectory=python/sdk"
```

With `uv`:

```bash
uv pip install "git+https://github.com/MalchuL/experiment_tracker.git@main#subdirectory=python/sdk"
```

For local examples in this repository, install the SDK into the example environment:

```bash
cd examples/training
uv sync
uv add ../../python/sdk
```

## Configure

Create an API token in the web UI, then save the backend URL and token:

```bash
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
```

Check that the backend is reachable and that the token is valid:

```bash
experiment-tracker ping
experiment-tracker whoami
```

The SDK also reads environment overrides with the `EXP_TRACKER_` prefix, including `EXP_TRACKER_BASE_URL`, `EXP_TRACKER_API_PREFIX`, `EXP_TRACKER_API_TOKEN`, `EXP_TRACKER_CONFIG_PATH`, and `EXP_TRACKER_SNAPSHOT_MAX_FILE_SIZE`.

## Choose an API

| Task | Use |
|------|-----|
| Log from training code | [`ExpTracker`](/docs/sdk/experiment-logging) |
| Configure credentials or run a script | [SDK CLI](/docs/sdk/cli) |
| Create, list, update, or delete resources from a shell | [SDK CLI resource commands](/docs/sdk/cli#resource-commands) |
| Build custom automation around request specs | [Low-level SDK API](/docs/sdk/low-level-api) |

## Minimal experiment

```python
from experiment_tracker_sdk import ExperimentStatus, ExpTracker, InitParams

tracker = ExpTracker.init(
    project="SDK Training",
    experiment="Baseline",
    init_params=InitParams(create_experiment_if_not_exists=True),
)

try:
    tracker.status(ExperimentStatus.RUNNING)
    for step in range(100):
        tracker.add_scalar("loss", 1.0 / (step + 1), global_step=step)
    tracker.add_metric("loss", 0.01, label="final")
    tracker.status(ExperimentStatus.COMPLETE)
finally:
    tracker.close()
```

## Example projects

- `examples/training` shows direct `ExpTracker` usage with scalar time series, final metrics, image/text step artifacts, and named final artifacts.
- `examples/pytorch-mnist-tensorboardx` shows `experiment-tracker run` with TensorBoardX hooks.
- `examples/training-wrong-logging` is for inspecting validation and UI behavior with intentionally mismatched artifact payloads.

## Related

- [Experiment logging with ExpTracker](/docs/sdk/experiment-logging)
- [SDK CLI](/docs/sdk/cli)
- [Low-level SDK API](/docs/sdk/low-level-api)
