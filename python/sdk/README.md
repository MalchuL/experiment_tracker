# Experiment Tracker SDK

Python SDK for sending experiment data to the Experiment Tracker backend.

## Install

From the repo root:

```
pip install -e /media/ssd_stuff/work/experiment_tracker/python/sdk
```

Or from the SDK folder:

```
pip install -e .
```

Using uv:

```
uv pip install -e /media/ssd_stuff/work/experiment_tracker/python/sdk
```

## Configure

Save the base URL and API token for the backend:

```
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
```

Check connectivity or token validity:

```
experiment-tracker ping
experiment-tracker whoami
```

## Use in code

Create a client and log metrics:

```
from experiment_tracker_sdk import ExperimentClient

client = ExperimentClient.from_config()
experiment = client.create_experiment(
    project_id="project-id",
    name="My Experiment",
    description="Baseline run",
)

client.log_metric(experiment.id, name="accuracy", value=0.91, step=1)
client.log_scalar(experiment.id, name="loss", value=0.42, step=1)
client.flush()
client.close()
```

If you prefer to pass config directly:

```
client = ExperimentClient(
    base_url="http://127.0.0.1:8000",
    api_token="<TOKEN>",
)
```
