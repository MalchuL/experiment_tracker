# Artifacts

Artifacts are files associated with experiments or projects. They store non-scalar outputs such as images, text, configs, models, reports, and future project-level objects.

There are three artifact flows:

- step artifacts;
- final experiment artifacts;
- project artifacts and snapshots.

## Step artifacts

Step artifacts are tied to a training step. Use them for outputs that belong on the scalars page:

- generated images;
- ground-truth images;
- text notes;
- sampled reports;
- other per-step outputs as support grows.

Currently the high-level SDK helpers cover images and text:

```python
tracker.add_image("generated", image, global_step=step)
tracker.add_text("training_note", "loss dropped after warmup", global_step=step)
```

Storage flow:

1. The backend uploads the file as an untracked experiment blob to object storage.
2. Object storage computes the content hash.
3. The backend logs artifact metadata to the scalars service `artifacts_info` table.
4. Downloads resolve metadata by experiment, step, name, and optional type, then fetch bytes from object storage by hash.

Step artifacts can be fetched by step and name. If multiple artifact types match the same step/name, pass the artifact type to disambiguate.

## Final experiment artifacts

Final experiment artifacts are named tracked files without a step. Use them for:

- run configs;
- model checkpoints;
- final confusion matrices;
- final images;
- package snapshots;
- JSON/YAML summaries;
- exported reports.

SDK helpers:

```python
tracker.log_final_artifact("model", model_bytes, stored_filepath="final/model.pt")
tracker.log_final_text("python_packages", installed_packages)
tracker.log_final_json("summary", {"accuracy": 0.94})
tracker.log_final_yaml("config", {"lr": 0.001})
tracker.log_final_image("confusion_matrix", image)
```

The unique key is `stored_filepath`. Uploading a new artifact to the same filepath replaces the old tracked artifact. If you upload the same filepath with a different name, the new name is stored and the file is overwritten.

This behavior is intentional: `name` is a friendly display label, while `stored_filepath` is the stable storage location. It lets a run update the same artifact path, such as `final/model.pt`.

## Project artifacts

Project artifacts are project-scoped content-addressed blobs. The SDK computes a hash, checks whether the project already has that hash, and uploads only missing content.

Use project artifacts for shared or reusable objects such as:

- code snapshots;
- dataset manifests;
- shared assets;
- files that multiple experiments may reference.

The backend already supports project artifact check, upload, download, delete, and snapshot operations through object storage. Product UI around this area is still emerging.

## Project snapshots

Snapshots are project-level archives that reference project CAS artifacts. They are useful for preserving a consistent set of project files such as code and config inputs.

Snapshot download returns a ZIP archive from object storage.

## CLI

Named final experiment artifacts can be managed from the CLI:

```bash
experiment-tracker experiment-artifact upsert \
  --experiment-id <experiment-id> \
  --file ./config.yaml \
  --filepath final/config.yaml \
  --name run_config

experiment-tracker experiment-artifact list --experiment-id <experiment-id>
experiment-tracker experiment-artifact download --experiment-id <experiment-id> --filepath final/config.yaml --output ./downloads
```

## Cleanup

Experiment cleanup can remove tracked experiment artifacts, at-step artifacts, or scalars separately. Project cleanup can remove project artifacts, snapshots, experiment buckets, or scalar tables.

## Related

- [SDK artifact logging](/docs/sdk/experiment-logging#step-artifacts)
- [Scalars](/docs/domains/scalars)
- [Projects: storage and cleanup](/docs/domains/projects#storage-and-cleanup)
