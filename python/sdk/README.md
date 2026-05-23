# Experiment Tracker SDK

Python SDK for sending experiment data to the Experiment Tracker backend.

## Install

From the repo root:

```
pip install -e <root_of_the_repo>/experiment_tracker/python/sdk
```

Or from the SDK folder:

```
pip install -e .
```

Using uv:

```
uv pip install -e <root_of_the_repo>/experiment_tracker/python/sdk
```

## Run tests

Install dev dependencies first:

```
uv pip install -e ".[dev]"
```

From the SDK folder:

```
uv run pytest
```

From the repo root:

```
uv run pytest python/sdk/tests
```

## Lint and type-check

Install dev dependencies first:

```
uv pip install -e ".[dev]"
```

From the SDK folder:

```
uv run ruff check src tests
uv run pyright src tests
```

## Configure

The bundled `experiment-tracker` CLI is implemented with [Click](https://click.palletsprojects.io/).

Optional environment defaults for interactive `experiment-tracker init` (when
you omit flags and press Enter at prompts) can be set with the `EXP_TRACKER_`
prefix, for example `EXP_TRACKER_DEFAULT_BASE_URL` and
`EXP_TRACKER_DEFAULT_API_PREFIX`. Values are read from the process environment
and an optional `.env` file in the current working directory (see
`experiment_tracker_sdk.settings`).

Save the base URL and API token for the backend:

```
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
```

Check connectivity or token validity:

```
experiment-tracker ping
experiment-tracker whoami
```

## Run a training script (`experiment-tracker run`)

For **simple experiments** (single-process or lightly threaded scripts), you can
launch a Python file so it runs as `__name__ == "__main__"`, with wrapper
options consumed before your script starts. Put arguments meant for your
script after `--`:

```
uv run experiment-tracker run --project mnist --offline train.py -- --epochs 10 --lr 1e-3
```

This mode uses `runpy` in the **current** process: bootstrap behavior and
`sys` changes persist. It is **not** a general-purpose launcher for distributed
or multiprocessing-heavy training. Use `experiment-tracker run --help` for the
full epilog.

## Use in code

Create a client and log metrics:

```
from experiment_tracker_sdk import ExperimentClient

client = ExperimentClient.from_config()
experiment = client.create_experiment(
    project_id="project-id",
    name="My Experiment",
    description="Baseline run",
)

client.log_metric(experiment.id, name="accuracy", value=0.91, step=1)
client.log_scalar(experiment.id, name="loss", value=0.42, step=1)
client.flush()
client.close()
```

If you prefer to pass config directly:

```
client = ExperimentClient(
    base_url="http://127.0.0.1:8000",
    api_token="<TOKEN>",
)
```
