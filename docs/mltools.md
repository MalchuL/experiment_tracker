# Feature Specification: Hyperparameter Logging and Importance Analysis

## 1. Overview

This feature adds first-class support for logging, displaying, comparing, and analyzing experiment hyperparameters in Experiment Tracker.

Hyperparameters are separate from experiment features. In the current product model, **features** describe semantic changes between experiments: architectural changes, enabled/disabled mechanisms, ablations, new losses, new modules, implementation changes, or research ideas. Hyperparameters, on the other hand, describe configurable training, model, optimizer, scheduler, dataset, and runtime parameters.

The feature introduces:

1. Hyperparameter logging through the SDK.
2. Hyperparameter editing/logging through the UI.
3. Hyperparameter storage in the backend as experiment data.
4. Hyperparameter display in the experiment sidebar.
5. Hyperparameter comparison between experiments.
6. A new `mltools` microservice for ML-specific analysis.
7. Asynchronous hyperparameter importance analysis jobs.
8. Random Forest based importance estimation for user-selected metrics.
9. Storage of trained models in object storage.
10. Storage of analysis metadata, results, warnings, and model references in the `mltools` database.

The first analytical capability of `mltools` is **hyperparameter importance analysis**. Future capabilities may include hyperparameter suggestion, experiment clustering, outlier detection, and automatic search-space recommendations.

---

## 2. Goals

The feature should allow users to:

1. Log experiment hyperparameters as nested JSON.
2. View hyperparameters in the UI.
3. Compare hyperparameters across experiments.
4. Start a hyperparameter importance analysis manually.
5. Select which target metrics should be used for the analysis.
6. Include all project experiments by default.
7. Exclude specific experiments from the analysis.
8. Exclude specific hyperparameters from the analysis.
9. Configure how each hyperparameter should be interpreted and processed.
10. Automatically infer basic hyperparameter types.
11. Train one Random Forest model per selected metric.
12. Store analysis results in a dedicated `mltools` database.
13. Store trained model artifacts in object storage.
14. Re-run the analysis with different settings.
15. Inspect warnings, skipped parameters, skipped experiments, and preprocessing issues.

---

## 3. Non-goals

The initial version does not aim to:

1. Automatically suggest the next best hyperparameters.
2. Run Bayesian optimization.
3. Perform full AutoML.
4. Use SHAP by default.
5. Train deep learning models for hyperparameter analysis.
6. Analyze raw text hyperparameters semantically.
7. Automatically start analysis after every experiment.
8. Use Compare-selected experiments as the analysis scope.
9. Replace the existing `features` system.
10. Store duplicated raw hyperparameter JSON inside the `mltools` database.

Hyperparameter suggestion can be implemented later as a separate phase.

---

## 4. Terminology

### 4.1. Experiment Features

Experiment features describe semantic changes in an experiment.

Examples:

```json
{
  "architecture": {
    "use_attention_block": true
  },
  "loss": {
    "added_contrastive_loss": true
  },
  "data": {
    "enabled_hard_negative_mining": true
  }
}
```

These are meant to explain what conceptually changed between experiments.

### 4.2. Hyperparameters

Hyperparameters describe configuration values used during training, evaluation, model construction, data preprocessing, optimization, or runtime setup.

Examples:

```json
{
  "optimizer": {
    "name": "adamw",
    "lr": 0.0003,
    "weight_decay": 0.01
  },
  "scheduler": {
    "type": "cosine",
    "warmup_steps": 500
  },
  "model": {
    "backbone": "resnet50",
    "dropout": 0.2
  },
  "training": {
    "batch_size": 32,
    "epochs": 50,
    "seed": 42
  }
}
```

### 4.3. Hyperparameter Importance Analysis

A manually started asynchronous analysis job that:

1. Fetches experiments, hyperparameters, and selected metrics.
2. Builds a tabular dataset.
3. Flattens nested hyperparameter JSON.
4. Infers and applies preprocessing rules.
5. Trains a separate Random Forest model for each selected target metric.
6. Computes hyperparameter importance.
7. Saves results, warnings, metadata, and model artifacts.

---

## 5. User Stories

### 5.1. Log Hyperparameters from SDK

As a user, I want to log hyperparameters from Python code so that I can later inspect and compare the configuration used for each experiment.

Example:

```python
tracker.log_hparams({
    "optimizer": {
        "name": "adamw",
        "lr": 3e-4,
        "weight_decay": 0.01,
    },
    "training": {
        "batch_size": 32,
        "epochs": 50,
        "seed": 42,
    },
    "model": {
        "backbone": "resnet50",
        "dropout": 0.2,
    },
})
```

### 5.2. View Hyperparameters in Experiment Sidebar

As a user, I want to open an experiment and see its hyperparameters in a dedicated sidebar tab.

### 5.3. Compare Hyperparameters

As a user, I want to compare hyperparameters between experiments to understand how training configuration differs between runs.

### 5.4. Run Importance Analysis

As a user, I want to manually start hyperparameter importance analysis for a project and select which metrics should be used as targets.

### 5.5. Exclude Parameters

As a user, I want to exclude specific hyperparameters from training, for example `seed`, `run_name`, `created_at`, or file paths, because they may be noisy or irrelevant.

### 5.6. Exclude Experiments

As a user, I want to exclude specific experiments from training, for example debug runs, broken runs, failed experiments, or experiments from a different dataset version.

### 5.7. Configure Parameter Types

As a user, I want to override inferred hyperparameter types and preprocessing strategies when automatic detection is wrong.

### 5.8. Inspect Warnings

As a user, I want to see why some parameters or experiments were skipped, so that the result is explainable and debuggable.

### 5.9. Recalculate Importance

As a user, I want to rerun the analysis after changing included experiments, selected metrics, excluded parameters, or preprocessing settings.

---

## 6. Backend Requirements

## 6.1. Hyperparameter Storage

Hyperparameters should be stored in the existing experiment data storage.

The backend should store them in `experiment_data` with:

```text
type = "hparams"
```

Expected conceptual schema:

```text
experiment_data
- id
- experiment_id
- type
- data
- created_at
- updated_at
```

Where:

```text
type = "hparams"
data = raw nested JSON object
```

The raw hyperparameter JSON should remain in the main backend database. The `mltools` service should not duplicate raw hyperparameter payloads in its own database.

---

## 6.2. Overwrite Behavior

Each experiment has one current hyperparameter JSON document.

If the user logs hyperparameters again for the same experiment, the previous hyperparameter document must be fully overwritten.

The default behavior should be:

```text
new hparams payload replaces the old hparams payload completely
```

No deep merge should be performed in the initial version.

Example:

Initial payload:

```json
{
  "optimizer": {
    "name": "adamw",
    "lr": 0.0003
  },
  "training": {
    "batch_size": 32
  }
}
```

Second payload:

```json
{
  "optimizer": {
    "name": "sgd",
    "lr": 0.01
  }
}
```

Final stored payload:

```json
{
  "optimizer": {
    "name": "sgd",
    "lr": 0.01
  }
}
```

The old `training.batch_size` value is removed.

---

## 6.3. Backend API for Hyperparameters

Suggested endpoints:

```text
POST /api/experiments/{experiment_id}/hparams
GET  /api/experiments/{experiment_id}/hparams
PUT  /api/experiments/{experiment_id}/hparams
DELETE /api/experiments/{experiment_id}/hparams
```

### 6.3.1. Create or Replace Hyperparameters

```http
PUT /api/experiments/{experiment_id}/hparams
```

Request:

```json
{
  "hparams": {
    "optimizer": {
      "name": "adamw",
      "lr": 0.0003
    },
    "training": {
      "batch_size": 32,
      "seed": 42
    }
  }
}
```

Response:

```json
{
  "experiment_id": "experiment_uuid",
  "type": "hparams",
  "hparams": {
    "optimizer": {
      "name": "adamw",
      "lr": 0.0003
    },
    "training": {
      "batch_size": 32,
      "seed": 42
    }
  },
  "created_at": "2026-06-07T12:00:00Z",
  "updated_at": "2026-06-07T12:00:00Z"
}
```

### 6.3.2. Get Hyperparameters

```http
GET /api/experiments/{experiment_id}/hparams
```

Response:

```json
{
  "experiment_id": "experiment_uuid",
  "hparams": {
    "optimizer": {
      "name": "adamw",
      "lr": 0.0003
    }
  }
}
```

If no hyperparameters are logged:

```json
{
  "experiment_id": "experiment_uuid",
  "hparams": null
}
```

### 6.3.3. Delete Hyperparameters

```http
DELETE /api/experiments/{experiment_id}/hparams
```

Deletes the current hyperparameter document for the experiment.

---

## 6.4. Backend API for Compare

Suggested endpoint:

```text
GET /api/projects/{project_id}/experiments/hparams/compare?experiment_ids=...
```

The response should provide hyperparameters for selected experiments in a format convenient for UI diff rendering.

Example response:

```json
{
  "project_id": "project_uuid",
  "experiments": [
    {
      "experiment_id": "exp_1",
      "experiment_name": "baseline",
      "hparams": {
        "optimizer": {
          "name": "adamw",
          "lr": 0.0003
        }
      }
    },
    {
      "experiment_id": "exp_2",
      "experiment_name": "higher lr",
      "hparams": {
        "optimizer": {
          "name": "adamw",
          "lr": 0.001
        }
      }
    }
  ]
}
```

---

## 6.5. Backend API for `mltools`

The UI should not need to know the internal location of the `mltools` service.

Recommended architecture:

```text
UI -> main backend -> mltools
```

The main backend should proxy or orchestrate requests to `mltools`.

This keeps:

1. Authentication centralized.
2. Authorization centralized.
3. UI API simpler.
4. Internal service topology hidden from the frontend.
5. CORS simpler.

Suggested backend-facing endpoints:

```text
POST /api/projects/{project_id}/mltools/hparams/importance/jobs
GET  /api/projects/{project_id}/mltools/hparams/importance/jobs
GET  /api/projects/{project_id}/mltools/hparams/importance/jobs/{job_id}
GET  /api/projects/{project_id}/mltools/hparams/importance/jobs/{job_id}/results
GET  /api/projects/{project_id}/mltools/hparams/importance/jobs/{job_id}/messages
```

---

## 7. SDK Requirements

## 7.1. Public SDK Method

Add:

```python
tracker.log_hparams(hparams: dict[str, Any]) -> None
```

Optional alias:

```python
tracker.log_hyperparameters(hparams: dict[str, Any]) -> None
```

The preferred method should be:

```python
log_hparams
```

---

## 7.2. SDK Behavior

The SDK should:

1. Accept a Python dictionary.
2. Validate that the payload can be serialized to JSON.
3. Convert common simple non-JSON types where safe.
4. Upload the payload to the backend.
5. Fully replace previous hyperparameters for the experiment.
6. Return a clear error if serialization fails.

---

## 7.3. Supported Automatic Conversions

The SDK may support safe conversions:

```text
Path -> str
Enum -> value
numpy scalar -> Python scalar
datetime -> ISO string
date -> ISO string
```

Unsupported objects should raise a clear error.

Example error:

```text
Failed to serialize hyperparameters. Key "optimizer.custom_object" contains unsupported type "MyOptimizerConfig".
```

---

## 7.4. Example SDK Usage

```python
from experiment_tracker import ExperimentTracker

tracker = ExperimentTracker(
    project_name="Image Classification",
    experiment_name="resnet50-adamw-lr-3e-4",
)

tracker.log_hparams({
    "optimizer": {
        "name": "adamw",
        "lr": 3e-4,
        "weight_decay": 0.01,
    },
    "scheduler": {
        "type": "cosine",
        "warmup_steps": 500,
    },
    "model": {
        "backbone": "resnet50",
        "dropout": 0.2,
    },
    "training": {
        "batch_size": 32,
        "epochs": 50,
        "seed": 42,
    },
})
```

---

## 8. UI Requirements

## 8.1. Experiment Sidebar

Add a dedicated `HParams` tab to the selected experiment sidebar.

Suggested sidebar tabs:

```text
Overview | Metrics | Features | HParams | Artifacts | Notes
```

The `HParams` tab should use the same or similar tree/JSON display component as the existing `Features` tab.

Minimum functionality:

1. Display nested JSON.
2. Expand and collapse nested objects.
3. Show scalar values.
4. Show value types.
5. Copy value.
6. Copy parameter path.
7. Show empty state if no hyperparameters are logged.
8. Allow editing or replacing hyperparameters if UI editing is supported.

Empty state example:

```text
No hyperparameters logged for this experiment.
Use the SDK or UI to add hyperparameters.
```

---

## 8.2. Hyperparameter Editing in UI

The UI should allow the user to add or replace hyperparameters manually.

Possible UI options:

1. JSON editor.
2. Form-based editor later.
3. Tree editor later.

For MVP, a JSON editor is enough.

Requirements:

1. Validate JSON before submitting.
2. Show parse errors clearly.
3. Confirm that saving will replace the previous hyperparameter document.
4. Send full JSON payload to backend.
5. Show success/error toast.

Confirmation text:

```text
Saving these hyperparameters will replace the existing hyperparameters for this experiment.
```

---

## 8.3. Compare UI

Add hyperparameter comparison support.

Suggested Compare tabs:

```text
Metrics | Features Diff | HParams Diff
```

`HParams Diff` should display differences between selected experiments.

Requirements:

1. Show nested JSON differences.
2. Highlight added, removed, and changed values.
3. Support multiple selected experiments.
4. Reuse existing diff rendering logic if possible.
5. Keep this separate from `features` comparison.

Important: selected experiments in Compare should not define the scope for hyperparameter importance analysis. Importance analysis uses all project experiments by default and has its own experiment exclusion settings.

---

## 8.4. Hyperparameter Importance UI

Add a separate UI area for hyperparameter importance analysis.

Possible locations:

Option A:

```text
Project -> Compare -> HParams Importance
```

Option B:

```text
Project -> ML Tools -> Hyperparameter Importance
```

Recommended initial design:

```text
Project -> ML Tools -> Hyperparameter Importance
```

Reason: importance analysis is not just visual comparison. It starts asynchronous training jobs, stores models, has history, uses all project experiments by default, and has its own settings.

The page should include:

1. Target metric selector.
2. Experiment inclusion/exclusion settings.
3. Hyperparameter inclusion/exclusion settings.
4. Parameter type and preprocessing settings.
5. Run analysis button.
6. Job status.
7. Results table.
8. Importance chart.
9. Warnings/errors panel.
10. Previous analysis jobs.

---

## 8.5. Target Metric Selection

The user manually selects which metrics should be used for analysis.

The service must not automatically choose target metrics.

UI should show available project metrics and allow selecting one or more.

Example:

```text
Target metrics:
[x] val_loss
[x] accuracy
[ ] train_loss
[ ] learning_rate
```

For each selected metric, `mltools` trains a separate model.

---

## 8.6. Experiment Scope

By default, the analysis should use all project experiments.

Compare-selected experiments should not participate in this logic.

Default scope:

```text
All experiments in the project
```

The analysis should then internally skip experiments that cannot be used for a specific metric or do not have hyperparameters.

Experiments may be excluded manually.

Possible filters:

```text
Include all experiments
Exclude selected experiments
Only completed experiments - optional future setting
Only experiments with hparams - internal filtering
Only experiments with selected metrics - internal filtering per metric
```

For MVP:

```text
Use all project experiments by default.
Allow manual experiment exclusion.
Skip invalid experiments during dataset construction.
```

---

## 8.7. Excluding Experiments

The UI should allow users to exclude experiments from the analysis.

For each excluded experiment, optionally store a reason.

Example:

```json
{
  "experiment_id": "exp_debug_1",
  "reason": "Debug run with broken dataset"
}
```

In the UI:

```text
Experiment                  Included
baseline                    yes
lr-3e-4                     yes
debug-run                   no
broken-augmentation-test    no
```

---

## 8.8. Excluding Hyperparameters

The UI should allow users to exclude hyperparameters from the analysis.

Common examples:

```text
seed
run_name
created_at
updated_at
checkpoint_path
output_dir
local_dataset_path
commit_hash
```

The UI should show:

```text
Path | Inferred type | Selected type | Processing | Included | Warnings
```

Example:

```text
training.seed           number    number    raw       disabled
optimizer.lr            number    number    log       enabled
optimizer.name          category  category  one-hot   enabled
checkpoint_path         text      ignored   ignored   disabled
```

---

## 8.9. Results UI

The results page should show one target metric at a time.

Table columns:

```text
Rank
Hyperparameter
Type
Processing
Importance
Missing values
Unique values
Warnings
```

Example:

```text
Rank | Hyperparameter        | Type     | Processing | Importance | Missing | Unique | Warnings
1    | optimizer.lr          | number   | log        | 0.34       | 0       | 12     | -
2    | model.dropout         | number   | raw        | 0.21       | 3       | 5      | missing values
3    | optimizer.name        | category | one-hot    | 0.13       | 0       | 4      | -
4    | training.batch_size   | number   | raw        | 0.09       | 1       | 6      | -
```

A bar chart should display feature importance values for the selected metric.

---

## 8.10. Job History UI

The UI should display previous analysis jobs.

Columns:

```text
Created at
Status
Target metrics
Experiment count
Parameter count
Model count
Created by
Duration
```

Users should be able to open a previous job and inspect its results.

---

## 9. `mltools` Service

## 9.1. Purpose

`mltools` is a separate microservice responsible for ML-specific operations that are outside the core CRUD responsibilities of the main backend.

Initial responsibility:

```text
Hyperparameter importance analysis
```

Future responsibilities may include:

```text
Hyperparameter suggestion
Experiment clustering
Metric trend analysis
Outlier detection
Search-space recommendation
```

---

## 9.2. Service Responsibilities

The `mltools` service should:

1. Accept requests to create hyperparameter importance jobs.
2. Use an API token to fetch data from the main backend.
3. Fetch all project experiments by default.
4. Fetch hyperparameters for experiments.
5. Fetch user-selected target metrics.
6. Build a dataset for each selected metric.
7. Flatten nested hyperparameter JSON.
8. Infer parameter types.
9. Apply preprocessing.
10. Respect excluded parameters.
11. Respect excluded experiments.
12. Train one Random Forest model per selected metric.
13. Compute hyperparameter importance.
14. Store trained models in object storage.
15. Store job metadata, results, warnings, and model references in its own database.
16. Expose job status and results to the backend.

---

## 9.3. Internal Authentication

`mltools` should access the main backend using an API token.

Required configuration:

```env
MLTOOLS_BACKEND_BASE_URL=http://backend:8000
MLTOOLS_BACKEND_API_TOKEN=...
```

Backend requests from `mltools` should include:

```http
Authorization: Bearer <MLTOOLS_BACKEND_API_TOKEN>
```

The backend should validate this token as an internal service token.

The token should allow only the required internal read operations:

1. Fetch project experiments.
2. Fetch experiment hyperparameters.
3. Fetch metric values for selected metrics.
4. Optionally fetch project metric metadata.

It should not grant unnecessary write access.

---

## 9.4. Object Storage

The trained model artifacts should be stored in object storage.

The service should support MinIO/S3-compatible storage.

Required configuration:

```env
MLTOOLS_OBJECT_STORAGE_ENDPOINT=http://minio:9000
MLTOOLS_OBJECT_STORAGE_ACCESS_KEY=...
MLTOOLS_OBJECT_STORAGE_SECRET_KEY=...
MLTOOLS_OBJECT_STORAGE_BUCKET=mltools
MLTOOLS_OBJECT_STORAGE_REGION=us-east-1
```

For each trained model, store:

1. Serialized model.
2. Preprocessing pipeline.
3. Feature mapping.
4. Model metadata.

Suggested artifact path:

```text
projects/{project_id}/hparam-importance/jobs/{job_id}/models/{target_metric}/model.pkl
```

Or safer normalized path:

```text
projects/{project_id}/hparam-importance/jobs/{job_id}/models/{target_metric_slug}/model.pkl
```

The `mltools` database should store only references to these objects, not the binary artifact itself.

---

## 10. Data Fetching

## 10.1. Fetch Project Experiments

By default, `mltools` should fetch all experiments from the project.

Compare-selected experiments should not be used as the analysis scope.

Required data:

```text
experiment_id
experiment_name
experiment_status
created_at
updated_at
```

Additional metadata may be fetched if needed.

---

## 10.2. Fetch Hyperparameters

For each experiment, fetch the current hyperparameter document from the backend.

If an experiment has no hyperparameters:

1. Skip it for analysis.
2. Add a warning message with category `missing_hparams`.

---

## 10.3. Fetch Target Metrics

The user manually selects target metrics.

For each selected metric, `mltools` should fetch metric values for all relevant experiments.

If a metric is missing for an experiment:

1. Skip that experiment only for this target metric.
2. Add a warning message with category `metric_missing`.
3. Continue training for other metrics.

---

## 10.4. Metric Value Selection

The user selects which metrics to analyze.

For each metric, the backend or `mltools` must decide which scalar value is used as the target.

Recommended behavior:

1. Use project-level metric direction if available.
2. If metric direction is `min`, use the minimum logged value.
3. If metric direction is `max`, use the maximum logged value.
4. If no direction is configured, use the last logged value and add a warning.

Example:

```text
val_loss -> min
accuracy -> max
f1_score -> max
train_loss -> min
```

This should be made explicit in the analysis metadata.

Stored metadata per metric:

```json
{
  "target_metric": "val_loss",
  "target_value_strategy": "min",
  "valid_experiment_count": 42
}
```

---

## 11. Flattening Hyperparameter JSON

## 11.1. Requirement

Nested JSON must be normalized into a flat dictionary before training.

Input:

```json
{
  "optimizer": {
    "name": "adamw",
    "lr": 0.0003
  },
  "model": {
    "dropout": 0.2
  }
}
```

Output:

```json
{
  "optimizer<sep>name": "adamw",
  "optimizer<sep>lr": 0.0003,
  "model<sep>dropout": 0.2
}
```

The separator should be configurable.

```env
MLTOOLS_HPARAM_PATH_SEPARATOR=<sep>
```

---

## 11.2. Reverse Mapping

For every flattened key, store the original JSON path.

Example:

```json
{
  "optimizer<sep>name": ["optimizer", "name"],
  "optimizer<sep>lr": ["optimizer", "lr"],
  "model<sep>dropout": ["model", "dropout"]
}
```

This mapping is required for:

1. UI display.
2. Debugging.
3. Model artifact metadata.
4. Reconstructing user-friendly parameter paths.
5. Explaining preprocessing warnings.

---

## 11.3. Separator Collision

If a JSON key already contains the configured separator, the service should handle it safely.

Possible behavior:

1. Escape separator inside key names.
2. Store reverse path mapping as source of truth.
3. Log a warning with category `path_separator_collision`.

The reverse path mapping should always be considered the canonical representation.

---

## 12. Array Handling

## 12.1. Default Behavior

Arrays should be skipped by default.

Example:

```json
{
  "layers": [128, 256, 512],
  "augmentations": ["flip", "crop"]
}
```

Default result:

```text
layers -> skipped
augmentations -> skipped
```

Warnings:

```text
unsupported_array
```

---

## 12.2. Optional Array Strategies

The system should support optional array processing strategies.

Supported strategies:

```text
skip
flatten_by_index
stringify_category
```

### 12.2.1. skip

Default strategy.

The array is ignored.

### 12.2.2. flatten_by_index

Array values are flattened by index.

Input:

```json
{
  "layers": [128, 256, 512]
}
```

Output:

```json
{
  "layers<sep>0": 128,
  "layers<sep>1": 256,
  "layers<sep>2": 512
}
```

This is useful for fixed-length arrays such as layer sizes.

### 12.2.3. stringify_category

The whole array is converted to a deterministic string and treated as a categorical value.

Input:

```json
{
  "augmentations": ["flip", "crop"]
}
```

Output:

```json
{
  "augmentations": "[\"flip\",\"crop\"]"
}
```

Then:

```text
augmentations -> category
```

This is useful when the array represents a categorical configuration.

---

## 12.3. Array Configuration

Array strategy can be configured globally and per parameter.

Environment default:

```env
MLTOOLS_DEFAULT_ARRAY_STRATEGY=skip
```

Per-parameter UI override:

```json
{
  "layers": {
    "array_strategy": "flatten_by_index"
  },
  "augmentations": {
    "array_strategy": "stringify_category"
  }
}
```

---

## 13. Type Inference

## 13.1. Supported Types

The system should support:

```text
number
category
boolean
date
datetime
text
array
unknown
ignored
```

---

## 13.2. Basic Inference Rules

The service should use simple deterministic heuristics.

Suggested rules:

```text
int or float -> number
bool -> boolean
short string -> category
ISO date string -> date
ISO datetime string -> datetime
long string -> text
array -> array
null -> missing
unsupported object -> unknown
```

Examples:

```text
0.0003 -> number
32 -> number
true -> boolean
"adamw" -> category
"resnet50" -> category
"2026-06-07" -> date
"2026-06-07T12:00:00Z" -> datetime
"/home/user/runs/exp_001/checkpoint.pt" -> text or ignored
```

---

## 13.3. Suspicious Parameter Names

Some parameter names are likely not useful for training or may cause data leakage.

The service should warn when key names contain suspicious tokens.

Examples:

```text
name
path
dir
file
uuid
id
hash
commit
created_at
updated_at
finished_at
result
metric
score
loss
accuracy
best
final
checkpoint
```

Warning category:

```text
suspicious_parameter_name
```

The service should not necessarily exclude them automatically, but the UI should make these warnings visible.

---

## 13.4. High-Cardinality Categories

Categorical features with too many unique values may be unhelpful or misleading.

Examples:

```text
run_name
checkpoint_path
commit_hash
dataset_file
```

If a categorical parameter has more unique values than the configured threshold, it should be marked with:

```text
high_cardinality_category
```

Config:

```env
MLTOOLS_MAX_CATEGORY_CARDINALITY=50
```

Default behavior:

```text
high-cardinality categories should be disabled or require explicit user confirmation
```

For MVP, they may be disabled automatically with a warning.

---

## 14. Preprocessing

## 14.1. Parameter Configuration

Each parameter should have configurable processing settings.

Conceptual structure:

```json
{
  "flat_key": "optimizer<sep>lr",
  "path": ["optimizer", "lr"],
  "inferred_type": "number",
  "selected_type": "number",
  "processing_strategy": "log",
  "included": true
}
```

---

## 14.2. Number Processing

Supported strategies:

```text
raw
standardize
log
disabled
```

Default:

```text
raw
```

If log transform is selected and value is invalid for log transform:

1. Set value to NaN.
2. Add warning `conversion_failed`.
3. Continue.

---

## 14.3. Category Processing

Supported strategies:

```text
one_hot
ordinal
disabled
```

Default:

```text
one_hot
```

For high-cardinality categories, default should be:

```text
disabled
```

or:

```text
one_hot only if unique_count <= MLTOOLS_MAX_CATEGORY_CARDINALITY
```

---

## 14.4. Boolean Processing

Supported strategies:

```text
as_int
disabled
```

Default:

```text
as_int
```

Mapping:

```text
true -> 1
false -> 0
missing -> NaN or configured missing value strategy
```

---

## 14.5. Date and Datetime Processing

Supported strategies:

```text
timestamp
extract_parts
disabled
```

Default:

```text
timestamp
```

`extract_parts` may create:

```text
year
month
day
day_of_week
hour
```

For MVP, `timestamp` is enough.

---

## 14.6. Text Processing

Default:

```text
disabled
```

Text values should not be used for training by default.

Reason:

1. They often contain names, paths, comments, or identifiers.
2. They may create leakage.
3. They may produce high-cardinality noise.
4. Meaningful NLP over text is outside MVP scope.

Optional strategy:

```text
stringify_category
```

This should be manually enabled by the user.

---

## 14.7. Unknown Types

Unknown types should be skipped by default.

Warning category:

```text
unsupported_type
```

---

## 14.8. Missing Values

The service should continue training when values are missing.

Missing values should not fail the entire job.

Recommended strategy:

```text
number -> median imputation or NaN-compatible strategy
category -> "__missing__"
boolean -> most frequent value or "__missing__" category before encoding
date/datetime -> median timestamp or NaN-compatible strategy
```

Configuration:

```env
MLTOOLS_MISSING_VALUE_STRATEGY=impute
```

If using a model implementation that does not support NaN directly, imputation is required.

---

## 15. Training

## 15.1. Model Type

The initial implementation should use Random Forest.

For metric prediction:

```text
RandomForestRegressor
```

Each selected metric is treated as a regression target.

---

## 15.2. One Model per Metric

For each user-selected metric, train a separate model.

Example selected metrics:

```text
val_loss
accuracy
f1_score
```

Models:

```text
RandomForestRegressor for val_loss
RandomForestRegressor for accuracy
RandomForestRegressor for f1_score
```

If an experiment does not have `val_loss`, it should be skipped only for the `val_loss` model.

If the same experiment has `accuracy`, it can still be used for the `accuracy` model.

---

## 15.3. Minimum Dataset Size

If too few valid experiments are available for a target metric, skip training for that metric.

Configuration:

```env
MLTOOLS_MIN_EXPERIMENTS_PER_METRIC=10
```

If not enough data:

1. Do not train model.
2. Save job message with category `insufficient_data`.
3. Continue processing other metrics.

---

## 15.4. Train/Validation Split

The service may use train/validation split to compute basic model quality metadata.

Configuration:

```env
MLTOOLS_RF_TEST_SIZE=0.2
```

For very small datasets, validation can be skipped.

---

## 15.5. Random Forest Configuration

Training parameters should be configured through environment variables.

Suggested variables:

```env
MLTOOLS_RF_N_ESTIMATORS=300
MLTOOLS_RF_MAX_DEPTH=
MLTOOLS_RF_MIN_SAMPLES_SPLIT=2
MLTOOLS_RF_MIN_SAMPLES_LEAF=1
MLTOOLS_RF_RANDOM_STATE=42
MLTOOLS_RF_N_JOBS=-1
MLTOOLS_RF_TEST_SIZE=0.2
MLTOOLS_RF_IMPORTANCE_METHOD=impurity
```

Additional useful variables:

```env
MLTOOLS_MIN_EXPERIMENTS_PER_METRIC=10
MLTOOLS_MAX_CATEGORY_CARDINALITY=50
MLTOOLS_MISSING_VALUE_STRATEGY=impute
MLTOOLS_DEFAULT_TEXT_STRATEGY=disabled
MLTOOLS_DEFAULT_ARRAY_STRATEGY=skip
MLTOOLS_HPARAM_PATH_SEPARATOR=<sep>
```

---

## 15.6. Importance Method

Initial method:

```text
impurity
```

This corresponds to Random Forest built-in `feature_importances_`.

The system should store the method name.

Future methods:

```text
permutation
shap
```

Important note: impurity-based importance may overestimate high-cardinality features. This should be documented and possibly shown in the UI.

---

## 16. Model Artifact Storage

## 16.1. What to Store

For each trained target metric model, store an artifact containing:

1. Trained Random Forest model.
2. Preprocessing pipeline.
3. Feature list.
4. Flattened-key to original-path mapping.
5. Type configuration.
6. Training configuration.
7. Library versions if possible.

The artifact can be serialized using `joblib` or another appropriate Python serialization format.

Example:

```text
model.joblib
```

---

## 16.2. Object Storage Path

Suggested object path:

```text
projects/{project_id}/hparam-importance/jobs/{job_id}/models/{target_metric_slug}/model.joblib
```

Example:

```text
projects/9e5d.../hparam-importance/jobs/a12b.../models/val_loss/model.joblib
```

---

## 16.3. Model Metadata in Database

The database should store model metadata and object storage reference.

Example:

```text
id
job_id
target_metric
model_type
object_storage_bucket
object_storage_key
train_rows
validation_rows
feature_count
score_name
score_value
created_at
```

The binary model should not be stored in the database.

---

## 17. Job Processing

## 17.1. Asynchronous Execution

Hyperparameter importance analysis must run asynchronously.

Recommended queue:

```text
Celery + Redis
```

Alternative options:

```text
Dramatiq
RQ
Arq
Temporal
```

For this project, Celery is a good default because the project already uses or plans to use Celery/Redis.

---

## 17.2. Job Statuses

Supported statuses:

```text
pending
running
completed
failed
cancelled
```

---

## 17.3. Job Lifecycle

Flow:

```text
1. User opens Hyperparameter Importance page.
2. User selects target metrics.
3. User optionally excludes experiments.
4. User optionally excludes or configures parameters.
5. User clicks Run analysis.
6. Backend creates an analysis job through mltools.
7. mltools stores job with status pending.
8. Celery worker picks up the job.
9. Job status becomes running.
10. mltools fetches project data from backend using API token.
11. mltools builds datasets.
12. mltools trains one model per selected metric.
13. mltools stores model artifacts in object storage.
14. mltools stores results in database.
15. Job status becomes completed or failed.
16. UI displays result.
```

---

## 17.4. Progress Reporting

The job should expose progress information.

Example stages:

```text
created
fetching_experiments
fetching_hparams
fetching_metrics
flattening_hparams
inferring_types
building_dataset
training_models
saving_models
saving_results
completed
failed
```

Progress payload example:

```json
{
  "status": "running",
  "stage": "training_models",
  "progress": 0.72,
  "message": "Training Random Forest for metric accuracy"
}
```

---

## 18. `mltools` Database Schema

The `mltools` service should have its own database.

It should not store raw hyperparameter JSON, but it should store analysis metadata, parameter metadata, model metadata, warnings, and results.

---

## 18.1. `hparam_importance_jobs`

Stores job-level metadata.

```text
id
project_id
status
target_metrics jsonb
requested_by_user_id
config jsonb
created_at
started_at
finished_at
duration_ms
error_message
```

Example `config`:

```json
{
  "rf": {
    "n_estimators": 300,
    "max_depth": null,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "random_state": 42,
    "n_jobs": -1
  },
  "preprocessing": {
    "missing_value_strategy": "impute",
    "default_array_strategy": "skip",
    "path_separator": "<sep>"
  }
}
```

---

## 18.2. `hparam_importance_job_experiments`

Stores experiment participation information.

```text
id
job_id
experiment_id
experiment_name
included boolean
exclude_reason nullable
has_hparams boolean
created_at
```

This table should record both included and excluded experiments.

---

## 18.3. `hparam_importance_job_metric_experiments`

Stores per-metric experiment usage.

```text
id
job_id
target_metric
experiment_id
used boolean
skip_reason nullable
target_value nullable
target_value_strategy nullable
```

This is important because an experiment may be used for one metric but skipped for another.

---

## 18.4. `hparam_importance_job_parameters`

Stores parameter-level metadata.

```text
id
job_id
flat_key
path jsonb
inferred_type
selected_type
processing_strategy
array_strategy nullable
included boolean
exclude_reason nullable
missing_count
unique_count
error_count
warning_count
created_at
```

Example:

```json
{
  "flat_key": "optimizer<sep>lr",
  "path": ["optimizer", "lr"],
  "inferred_type": "number",
  "selected_type": "number",
  "processing_strategy": "log",
  "included": true,
  "missing_count": 0,
  "unique_count": 12
}
```

---

## 18.5. `hparam_importance_results`

Stores importance values.

```text
id
job_id
target_metric
flat_key
path jsonb
importance
rank
importance_method
created_at
```

Example:

```text
target_metric = "val_loss"
flat_key = "optimizer<sep>lr"
importance = 0.34
rank = 1
importance_method = "impurity"
```

---

## 18.6. `hparam_importance_model_artifacts`

Stores model artifact metadata.

```text
id
job_id
target_metric
model_type
object_storage_bucket
object_storage_key
artifact_format
train_rows
validation_rows
feature_count
score_name nullable
score_value nullable
created_at
```

Example:

```text
model_type = "RandomForestRegressor"
artifact_format = "joblib"
object_storage_key = "projects/{project_id}/hparam-importance/jobs/{job_id}/models/val_loss/model.joblib"
```

---

## 18.7. `hparam_importance_job_messages`

Stores warnings, errors, and informational messages.

```text
id
job_id
level
category
message
experiment_id nullable
flat_key nullable
target_metric nullable
created_at
```

Levels:

```text
info
warning
error
```

Categories:

```text
missing_hparams
missing_value
conversion_failed
unsupported_type
unsupported_array
high_cardinality_category
constant_feature
mostly_missing_feature
invalid_date
excluded_by_user
excluded_experiment
metric_missing
insufficient_data
training_failed
model_save_failed
path_separator_collision
suspicious_parameter_name
```

---

## 19. API Contracts for `mltools`

## 19.1. Create Job

```http
POST /internal/mltools/projects/{project_id}/hparams/importance/jobs
```

Request:

```json
{
  "target_metrics": ["val_loss", "accuracy"],
  "excluded_experiment_ids": ["exp_debug_1"],
  "excluded_hparams": [
    "training<sep>seed",
    "runtime<sep>run_name",
    "paths<sep>checkpoint_path"
  ],
  "parameter_overrides": {
    "optimizer<sep>lr": {
      "selected_type": "number",
      "processing_strategy": "log"
    },
    "optimizer<sep>name": {
      "selected_type": "category",
      "processing_strategy": "one_hot"
    },
    "layers": {
      "selected_type": "array",
      "array_strategy": "flatten_by_index"
    },
    "augmentations": {
      "selected_type": "array",
      "array_strategy": "stringify_category"
    }
  }
}
```

Response:

```json
{
  "job_id": "job_uuid",
  "status": "pending"
}
```

---

## 19.2. Get Job

```http
GET /internal/mltools/projects/{project_id}/hparams/importance/jobs/{job_id}
```

Response:

```json
{
  "job_id": "job_uuid",
  "project_id": "project_uuid",
  "status": "running",
  "stage": "training_models",
  "progress": 0.72,
  "target_metrics": ["val_loss", "accuracy"],
  "created_at": "2026-06-07T12:00:00Z",
  "started_at": "2026-06-07T12:01:00Z",
  "finished_at": null,
  "error_message": null
}
```

---

## 19.3. Get Results

```http
GET /internal/mltools/projects/{project_id}/hparams/importance/jobs/{job_id}/results
```

Response:

```json
{
  "job_id": "job_uuid",
  "results": [
    {
      "target_metric": "val_loss",
      "items": [
        {
          "rank": 1,
          "flat_key": "optimizer<sep>lr",
          "path": ["optimizer", "lr"],
          "importance": 0.34,
          "importance_method": "impurity",
          "selected_type": "number",
          "processing_strategy": "log"
        }
      ]
    }
  ]
}
```

---

## 19.4. Get Messages

```http
GET /internal/mltools/projects/{project_id}/hparams/importance/jobs/{job_id}/messages
```

Response:

```json
{
  "job_id": "job_uuid",
  "messages": [
    {
      "level": "warning",
      "category": "metric_missing",
      "message": "Metric val_loss is missing for experiment exp_123. Experiment was skipped for this metric.",
      "experiment_id": "exp_123",
      "flat_key": null,
      "target_metric": "val_loss",
      "created_at": "2026-06-07T12:01:10Z"
    }
  ]
}
```

---

## 20. Error Handling

## 20.1. General Principle

The analysis should be fault-tolerant.

A single bad parameter, missing value, failed conversion, missing metric, or skipped experiment should not fail the whole job.

The job should fail only when a critical system-level error happens.

Examples of critical errors:

```text
backend unavailable
database unavailable
object storage unavailable during required model save
invalid job configuration
no target metrics selected
all selected metrics failed
unexpected training exception
```

---

## 20.2. Non-critical Errors

These should be logged and the job should continue:

```text
missing hparams for one experiment
missing metric for one experiment
failed value conversion for one parameter
unsupported array strategy for one parameter
invalid date string
high-cardinality category
constant feature
mostly missing feature
```

---

## 20.3. Failed Job

If the job fails, store:

```text
status = failed
error_message
finished_at
messages
```

The UI should show the error and any partial messages.

---

## 21. Configuration

Suggested environment variables:

```env
# Backend
MLTOOLS_BACKEND_BASE_URL=http://backend:8000
MLTOOLS_BACKEND_API_TOKEN=

# Database
MLTOOLS_DATABASE_URL=postgresql+asyncpg://mltools:mltools@postgres:5432/mltools

# Queue
MLTOOLS_REDIS_URL=redis://redis:6379/0
MLTOOLS_CELERY_BROKER_URL=redis://redis:6379/0
MLTOOLS_CELERY_RESULT_BACKEND=redis://redis:6379/1

# Object storage
MLTOOLS_OBJECT_STORAGE_ENDPOINT=http://minio:9000
MLTOOLS_OBJECT_STORAGE_ACCESS_KEY=
MLTOOLS_OBJECT_STORAGE_SECRET_KEY=
MLTOOLS_OBJECT_STORAGE_BUCKET=mltools
MLTOOLS_OBJECT_STORAGE_REGION=us-east-1

# Hyperparameter processing
MLTOOLS_HPARAM_PATH_SEPARATOR=<sep>
MLTOOLS_DEFAULT_ARRAY_STRATEGY=skip
MLTOOLS_DEFAULT_TEXT_STRATEGY=disabled
MLTOOLS_MAX_CATEGORY_CARDINALITY=50
MLTOOLS_MISSING_VALUE_STRATEGY=impute
MLTOOLS_MIN_EXPERIMENTS_PER_METRIC=10

# Random Forest
MLTOOLS_RF_N_ESTIMATORS=300
MLTOOLS_RF_MAX_DEPTH=
MLTOOLS_RF_MIN_SAMPLES_SPLIT=2
MLTOOLS_RF_MIN_SAMPLES_LEAF=1
MLTOOLS_RF_RANDOM_STATE=42
MLTOOLS_RF_N_JOBS=-1
MLTOOLS_RF_TEST_SIZE=0.2
MLTOOLS_RF_IMPORTANCE_METHOD=impurity
```

---

## 22. Suggested Implementation Phases

## Phase 1: Hyperparameter Logging

Scope:

1. Backend `hparams` storage in `experiment_data`.
2. SDK `log_hparams`.
3. UI experiment sidebar `HParams` tab.
4. UI manual JSON edit/replace.
5. Basic backend API.

Acceptance criteria:

1. User can log hyperparameters from SDK.
2. User can view hyperparameters in experiment sidebar.
3. User can replace hyperparameters from UI.
4. New hparams replace old hparams completely.
5. Hyperparameters are stored as `experiment_data.type = "hparams"`.

---

## Phase 2: Hyperparameter Compare

Scope:

1. Backend compare endpoint.
2. UI `HParams Diff` tab.
3. Nested JSON diff rendering.
4. Added/removed/changed highlighting.

Acceptance criteria:

1. User can select experiments and compare hyperparameters.
2. UI clearly separates `Features Diff` and `HParams Diff`.
3. Missing hparams are handled gracefully.

---

## Phase 3: `mltools` Service Skeleton

Scope:

1. New `mltools` service.
2. Separate database.
3. API token authentication to backend.
4. Job creation API.
5. Celery/Redis worker.
6. Job status tracking.
7. Object storage connection.

Acceptance criteria:

1. Backend can create an `mltools` job.
2. Job status changes from `pending` to `running`.
3. Job can fetch experiments from backend.
4. Job can store metadata in `mltools` database.
5. Job can connect to object storage.

---

## Phase 4: Dataset Builder

Scope:

1. Fetch all project experiments.
2. Fetch hparams.
3. Fetch selected target metrics.
4. Flatten hparams.
5. Build reverse path mapping.
6. Skip arrays by default.
7. Support `flatten_by_index`.
8. Support `stringify_category`.
9. Infer types.
10. Apply exclusions.

Acceptance criteria:

1. Nested hparams are converted to flat table.
2. Reverse mapping is stored.
3. Arrays are skipped by default.
4. Array strategy can be overridden.
5. Experiments without hparams are skipped with warnings.
6. Experiments missing a target metric are skipped only for that metric.
7. Excluded experiments and parameters are not used.

---

## Phase 5: Training and Importance Results

Scope:

1. Train one Random Forest model per selected metric.
2. Use env-configured Random Forest parameters.
3. Apply preprocessing.
4. Handle missing values.
5. Compute feature importance.
6. Save results to database.
7. Save trained model artifacts to object storage.
8. Save model metadata.

Acceptance criteria:

1. A separate model is trained for each selected metric.
2. Importance results are stored per metric.
3. Model artifacts are stored in object storage.
4. Model references are stored in the database.
5. Training continues when individual parameters have conversion issues.
6. Metrics with insufficient data are skipped with warnings.

---

## Phase 6: Importance UI

Scope:

1. Hyperparameter Importance page.
2. Target metric selector.
3. Excluded experiment selector.
4. Excluded parameter selector.
5. Parameter type/preprocessing settings.
6. Run analysis button.
7. Job status display.
8. Results table.
9. Importance chart.
10. Warnings/errors panel.
11. Job history.

Acceptance criteria:

1. User can start a new analysis job.
2. User can select target metrics.
3. User can exclude experiments.
4. User can exclude parameters.
5. User can override parameter type and preprocessing.
6. User can see job progress.
7. User can view results after completion.
8. User can inspect warnings and skipped data.
9. User can open previous jobs.

---

## 23. Acceptance Criteria

The feature is complete when:

1. Hyperparameters can be logged through the SDK.
2. Hyperparameters can be logged or replaced through the UI.
3. Hyperparameters are stored in `experiment_data` with type `hparams`.
4. Re-logging hyperparameters fully replaces the previous hyperparameter document.
5. Hyperparameters are displayed in the experiment sidebar.
6. Hyperparameters can be compared between experiments.
7. `mltools` exists as a separate microservice.
8. `mltools` can fetch data from the backend using an API token.
9. `mltools` uses all project experiments by default for analysis.
10. Compare-selected experiments do not define the analysis scope.
11. The user manually selects target metrics for analysis.
12. For each selected metric, a separate Random Forest model is trained.
13. Experiments missing a selected metric are skipped only for that metric.
14. Nested hparams are flattened using a configurable separator.
15. Reverse mapping from flat keys to original JSON paths is preserved.
16. Arrays are skipped by default.
17. Arrays can optionally be flattened by index.
18. Arrays can optionally be stringified and treated as categories.
19. Parameter types are inferred automatically with simple rules.
20. Users can override parameter type and preprocessing.
21. Users can exclude parameters.
22. Users can exclude experiments.
23. Preprocessing errors are logged but do not fail the whole job.
24. Missing values are handled without failing training.
25. Trained model artifacts are saved to object storage.
26. Model artifact references are saved in the `mltools` database.
27. Importance results are saved in the `mltools` database.
28. Job warnings and errors are visible in the UI.
29. Users can rerun analysis with different settings.
30. Previous analysis jobs can be inspected.

---

## 24. Future Improvements

The following features are intentionally out of MVP scope but should be considered later.

### 24.1. Hyperparameter Suggestion

Use previous experiments to suggest promising next hyperparameters.

Possible approaches:

```text
Bayesian optimization
Surrogate model optimization
Random Forest regression + search space sampling
Tree-structured Parzen Estimator
Evolutionary search
```

### 24.2. Permutation Importance

Add permutation importance as an alternative to impurity-based importance.

Reason: impurity-based importance can be biased toward high-cardinality features.

### 24.3. SHAP Support

Add SHAP values for better interpretability.

### 24.4. Parameter-vs-Metric Plots

Show direct visual relationship between a parameter and a selected metric.

Examples:

```text
learning_rate vs val_loss
batch_size vs accuracy
dropout vs f1_score
```

### 24.5. Search Space Definition

Allow users to define expected hyperparameter search spaces.

Example:

```json
{
  "optimizer.lr": {
    "type": "float",
    "min": 0.00001,
    "max": 0.01,
    "scale": "log"
  },
  "training.batch_size": {
    "type": "int",
    "values": [16, 32, 64, 128]
  }
}
```

### 24.6. Automatic Leakage Detection

Improve detection of parameters that may leak target information.

Examples:

```text
best_accuracy
final_loss
selected_epoch
early_stopping_epoch
checkpoint_with_best_score
```

### 24.7. Dataset Version Awareness

Allow users to group or filter analysis by dataset version.

This is important because hyperparameter importance may be meaningless if experiments were run on different datasets.

---

## 25. Main Design Decisions

The final design uses the following decisions:

1. Hyperparameters are stored as nested JSON.
2. Hyperparameters are stored in `experiment_data` with type `hparams`.
3. Hyperparameters are separate from experiment features.
4. Re-logging hyperparameters fully replaces the previous hyperparameter document.
5. The user manually starts importance analysis.
6. The user manually selects target metrics.
7. All project experiments are used by default.
8. Compare-selected experiments are not used as analysis scope.
9. Arrays are skipped by default.
10. Arrays can optionally be flattened by index.
11. Arrays can optionally be converted to string categories.
12. `mltools` fetches backend data using an API token.
13. `mltools` stores its own metadata and results in a separate database.
14. Raw hyperparameter JSON is not duplicated in the `mltools` database.
15. Trained models are stored in object storage.
16. Model artifact references are stored in the `mltools` database.
17. The first analysis algorithm is Random Forest based importance estimation.
18. One model is trained per selected target metric.
19. Missing metrics skip experiments only for the affected metric.
20. Preprocessing errors are logged and do not stop the whole analysis.
