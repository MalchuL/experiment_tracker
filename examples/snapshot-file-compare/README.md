# Snapshot File Compare Example

This example generates a synthetic training workspace with up to **30 snapshot-included files**, mutates source/config/report files, logs scalars, and stores the generated files as an experiment snapshot. Run it multiple times with different variants or `--random-training`, then open **Compare -> Files** in the web UI and select those experiments.

## Setup

```bash
cd examples/snapshot-file-compare
uv sync
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
```

## Run Deterministic Variants

```bash
uv run python train.py --experiment-name "Snapshot baseline" --variant baseline --seed 7
uv run python train.py --experiment-name "Snapshot dropout" --variant dropout --seed 7
```

## Run Random Training

```bash
uv run python train.py --experiment-name "Snapshot random" --random-training
```

Preview what will be included in the snapshot:

```bash
uv run exp-tracker check-files training_files --ignore-file .exp_tracker_ignore
```
