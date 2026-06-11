# TensorBoard Patch Example

Minimal synthetic training loop that logs through **TensorBoardX**
(`SummaryWriter`) instead of calling `ExpTracker.add_scalar` directly. No
PyTorch is required.

The script calls `monkey_patch_tensorboard(tracker)` so TensorBoard writes are
mirrored to the Experiment Tracker backend while still producing local event
files under `runs/`.

This is a lighter alternative to `examples/training`: fewer steps, no final
artifacts, and no direct tracker logging APIs in the training loop.

## Setup

From this folder:

```bash
uv sync
```

Configure the SDK once:

```bash
uv run experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
```

## Run

Fast smoke test (no sleep between steps):

```bash
uv run python train.py --steps 20 --sleep 0
```

Default run (~30 steps, short pause between steps):

```bash
uv run python train.py
```

Custom project and experiment names:

```bash
uv run python train.py \
  --project-name "My Project" \
  --experiment-name "TB patch demo" \
  --steps 50
```

After the run, open the experiment in the web UI to see scalars, images, and
histograms logged via the TensorBoard hook. Local TensorBoard event files remain
in `runs/tensorboard-patch/`.
