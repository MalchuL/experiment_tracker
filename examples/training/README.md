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
uv run experiment-tracker run --project mnist train.py -- --epochs 100 --max-train-batches 100 --max-val-batches 100
```
