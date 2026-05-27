# PyTorch MNIST TensorBoardX Example

This example is a small MNIST classifier intended to run through
`experiment-tracker run`. The training script uses PyTorch and
`tensorboardX.SummaryWriter` directly; it does not import the Experiment Tracker
SDK.

## Setup

From this folder:

```bash
uv sync
```

Configure the tracker CLI once:

```bash
uv run experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
```

## Run

Run a short offline smoke test:

```bash
uv run experiment-tracker run --project mnist train.py -- --epochs 1 --max-train-batches 2 --max-val-batches 1
```

Run the default quick example:

```bash
uv run experiment-tracker run --project mnist train.py
```

The first run downloads MNIST into `data/`. TensorBoardX event files are written
under `runs/`.
