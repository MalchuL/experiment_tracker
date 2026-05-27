# SDK CLI

The SDK installs three equivalent console entry points:

- `experiment-tracker`
- `exp-tracker`
- `exp-track`

Examples below use `experiment-tracker`, but the shorter aliases call the same CLI.

## Configure and inspect

Save the backend URL and API token:

```bash
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
```

Check the API and current token:

```bash
experiment-tracker ping
experiment-tracker whoami
```

Remove the default SDK configuration directory:

```bash
experiment-tracker clean-config
```

Use `-y` to skip the confirmation prompt:

```bash
experiment-tracker clean-config -y
```

The CLI reads saved config plus `EXP_TRACKER_` environment overrides, including `EXP_TRACKER_BASE_URL`, `EXP_TRACKER_API_PREFIX`, `EXP_TRACKER_API_TOKEN`, and `EXP_TRACKER_CONFIG_PATH`.

## Run a script

`experiment-tracker run` executes a Python file as `__main__` after applying SDK bootstrap behavior.

```bash
experiment-tracker run --project mnist train.py -- --epochs 10 --lr 1e-3
```

Wrapper options belong before the script path:

```bash
experiment-tracker run --project mnist --team research --experiment baseline train.py
```

Arguments for your training script belong after a lone `--` separator:

```bash
experiment-tracker run --project mnist train.py -- --epochs 5 --batch-size 128
```

Use offline mode when you only want local bootstrap behavior and do not want the wrapper to create or update a remote experiment:

```bash
experiment-tracker run --project mnist --offline train.py -- --epochs 1
```

:::warning
`experiment-tracker run` uses Python `runpy` in the current process. It is intended for simple single-process or lightly threaded scripts, local debugging, and one-off research runs. It is not a general launcher for distributed PyTorch, elastic multi-node jobs, or heavy multiprocessing.
:::

## TensorBoardX hook example

The `examples/pytorch-mnist-tensorboardx` project uses `tensorboardX.SummaryWriter` directly. Running it through `experiment-tracker run` registers the default TensorBoard hooks before the script starts:

```bash
cd examples/pytorch-mnist-tensorboardx
uv sync
uv run experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
uv run experiment-tracker run --project mnist train.py -- --epochs 1 --max-train-batches 2 --max-val-batches 1
```

The first run downloads MNIST into `data/`. TensorBoardX event files are written under `runs/`.

## Resource commands

The CLI exposes resource commands for scripts, admin jobs, and one-off inspection.

### Teams

```bash
experiment-tracker team list
experiment-tracker team get <team-id>
experiment-tracker team create --name "Research" --description "Research team"
experiment-tracker team update <team-id> --name "Research"
experiment-tracker team delete <team-id> -y
```

### Projects

```bash
experiment-tracker project list
experiment-tracker project get <project-id>
experiment-tracker project create --name "MNIST" --description "Classifier runs"
experiment-tracker project update <project-id> --name "MNIST v2"
experiment-tracker project delete <project-id> -y
```

### Experiments

```bash
experiment-tracker experiment list --project-id <project-id>
experiment-tracker experiment get <experiment-id>
experiment-tracker experiment create --project-id <project-id> --name "Baseline"
experiment-tracker experiment update <experiment-id> --status running --progress 50
experiment-tracker experiment delete <experiment-id> -y
```

Experiment create and update also support description, color, parent experiment id, and repeated `--tag` values.

### Metrics

```bash
experiment-tracker metric list --experiment-id <experiment-id>
experiment-tracker metric list --project-id <project-id>
experiment-tracker metric get --experiment-id <experiment-id> --name accuracy --label final
experiment-tracker metric upsert --experiment-id <experiment-id> --label final --name accuracy --value 0.94
experiment-tracker metric dump --project-id <project-id> --label final --format table
```

`metric dump` supports `table`, `json`, `csv`, and `md` output.

### Named experiment artifacts

Named experiment artifacts are final, no-step artifacts such as configs, checkpoints, and exports.

```bash
experiment-tracker experiment-artifact list --experiment-id <experiment-id>
experiment-tracker experiment-artifact upsert --experiment-id <experiment-id> --file ./model.pt --filepath final/model.pt --name model
experiment-tracker experiment-artifact get --experiment-id <experiment-id> --filepath final/model.pt
experiment-tracker experiment-artifact download --experiment-id <experiment-id> --filepath final/model.pt --output ./downloads
experiment-tracker experiment-artifact delete --experiment-id <experiment-id> --filepath final/model.pt -y
```

Artifact get, download, and delete accept one identifier: `--filepath`, `--blob-id`, or `--artifact-hash`.

## Help

Every command supports `--help`:

```bash
experiment-tracker --help
experiment-tracker run --help
experiment-tracker metric dump --help
```
