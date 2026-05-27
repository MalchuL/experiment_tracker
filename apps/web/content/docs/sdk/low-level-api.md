# Low-level SDK API

Use `ExpTracker` for normal training scripts. The lower-level SDK APIs are useful when building automation, custom command-line tools, notebooks, or integration tests that need explicit control over requests.

## Client and registry

`ExpTrackerApiAccess` builds SDK request dependencies from saved configuration.

```python
from experiment_tracker_sdk.client.api_access import ExpTrackerApiAccess

access = ExpTrackerApiAccess.instance()
client = access.get_request_client()
registry = access.get_api_requests_registry()

profile = client.request(registry.users.get_my_profile())
print(profile.email)

client.close()
```

The registry creates typed request specs. The client executes them and parses JSON responses into the configured Pydantic response models.

```python
projects = client.request(registry.projects.get_all_projects(limit=20, offset=0))

project = client.request(
    registry.projects.create_project(
        name="SDK Automation",
        description="Created from a low-level SDK script",
        team_id=None,
    )
)
```

When using the low-level client directly, close it when your script is done.

## Direct client construction

If you do not want to read the saved SDK config, construct a client explicitly:

```python
from experiment_tracker_sdk.client.api_registry import APIRequestsRegistry
from experiment_tracker_sdk.client.client import ExperimentTrackerClient

client = ExperimentTrackerClient(
    base_url="http://127.0.0.1:8000",
    api_token="<TOKEN>",
    api_prefix="/api",
)
registry = APIRequestsRegistry()

health = client.request(registry.health.get_healthcheck())
print(health)

client.close()
```

## Builder and instance style

The SDK also exposes object wrappers for common resources:

- `TeamInstance`
- `ProjectInstance`
- `ExperimentInstance`
- `MetricInstance`

Builders create resources and instances update mutable fields on the server.

```python
from experiment_tracker_sdk import ExperimentInstance, ExperimentStatus

experiment = (
    ExperimentInstance.builder()
    .project_id("<project-id>")
    .name("Low-level baseline")
    .description("Created through the SDK builder")
    .status(ExperimentStatus.PLANNED)
    .tags(["sdk", "builder"])
    .create()
)

experiment.status = ExperimentStatus.RUNNING
experiment.progress = 50
experiment.description = "Halfway through"
experiment.status = ExperimentStatus.COMPLETE
experiment.progress = 100
```

Instances can also fetch existing resources by id:

```python
experiment = ExperimentInstance.fetch("<experiment-id>")
print(experiment.name)
```

:::note
For high-volume scalar logging, prefer `ExpTracker.add_scalar(...)`. It uses the SDK's scalar batching strategy, while direct low-level calls are better suited to management operations and custom tooling.
:::

## Named experiment artifacts

Named experiment artifacts are final artifacts without a step. They are useful for configs, checkpoints, reports, and exports.

The CLI provides the simplest low-level operational path:

```bash
experiment-tracker experiment-artifact upsert \
  --experiment-id <experiment-id> \
  --file ./config.yaml \
  --filepath final/config.yaml \
  --name run_config

experiment-tracker experiment-artifact list --experiment-id <experiment-id>

experiment-tracker experiment-artifact download \
  --experiment-id <experiment-id> \
  --filepath final/config.yaml \
  --output ./downloads
```

The same domain is available through request specs:

```python
from pathlib import Path

from experiment_tracker_sdk.client.request_types import FileUploadSpec

file_path = Path("config.yaml")
artifact = client.request(
    registry.experiment_artifacts.upsert_named_experiment_artifact(
        experiment_id="<experiment-id>",
        filepath="final/config.yaml",
        file=FileUploadSpec(
            content=file_path.read_bytes(),
            filename=file_path.name,
            content_type="application/x-yaml",
        ),
        name="run_config",
    )
)
```

Use `ExpTracker.log_final_artifact(...)` and its typed helpers when this upload happens as part of a training script.

## Pagination helpers

For common list operations, the public SDK surface includes convenience fetchers:

```python
from experiment_tracker_sdk import (
    fetch_all_project_experiments,
    fetch_all_projects,
    fetch_all_recent_experiments,
    fetch_all_teams,
)

projects = fetch_all_projects()
teams = fetch_all_teams()
recent = fetch_all_recent_experiments()
project_runs = fetch_all_project_experiments("<project-id>")
```

These helpers use the configured SDK client and collect paginated results for you.
