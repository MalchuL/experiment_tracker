"""Resource command registration for the ``experiment-tracker`` CLI."""

from __future__ import annotations

from .resources_impl.experiment_artifacts import experiment_artifact_group
from .resources_impl.experiments import experiment_group
from .resources_impl.metrics import metric_group
from .resources_impl.projects import project_group
from .resources_impl.teams import team_group

RESOURCE_COMMANDS = (
    project_group,
    team_group,
    experiment_group,
    metric_group,
    experiment_artifact_group,
)

