"""Domain command registration for the ``experiment-tracker`` CLI."""

from __future__ import annotations

from .domain_cli.experiment_artifacts import experiment_artifact_group
from .domain_cli.experiments import experiment_group
from .domain_cli.metrics import metric_group
from .domain_cli.projects import project_group
from .domain_cli.teams import team_group

DOMAIN_COMMANDS = (
    project_group,
    team_group,
    experiment_group,
    metric_group,
    experiment_artifact_group,
)
