# Training Example

This example runs a 1-minute random training loop and logs metrics to the
Experiment Tracker backend using the SDK.

## Setup

Install the SDK and configure it:

```
cd examples/training
uv sync
uv add ../../python/sdk
```

```
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
```

## Run

From the examples/training folder:

```
uv run python train.py --project-name "SDK Training" --team-name "Demo Team"
```

If `--team-name` is omitted, the project is created without a team.
