# Verbose large artifact transfer

Demonstrates **tqdm progress bars** while uploading and downloading several **named experiment artifacts** (each JSON file is at least **50 MiB** by default).

Each file is a compact UTF-8 JSON document (`structured_json.py`) with:

- `format`, `version`, `artifact_index`, `record_count`
- `records`: a large array of deterministic objects (`id`, `step`, `metric`, `phase`)

After download, the script checks **byte-for-byte equality** and that the **parsed JSON** deep-equals the upload (schema validation plus `==` on the full object tree).

Requires a configured SDK (`experiment-tracker init`) and a running Experiment Tracker API (local stack or remote).

## Run

```bash
cd examples/verbose-artifact-transfer
uv sync
uv run python train.py --project-name "SDK Verbose Artifacts" --experiment-name "Large transfer demo"
```

Optional flags:

- `--artifact-count 3` — number of files (default `3`)
- `--file-size-mib 55` — minimum size per file in MiB (minimum `50`)
- `--data-dir .data` — where upload payloads and downloads are stored
- `--skip-download` — upload only

Generated payloads live under `.data/uploads/`; downloaded copies under `.data/downloads/` (gitignored).
