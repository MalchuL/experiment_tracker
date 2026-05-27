from __future__ import annotations

from dataclasses import dataclass

from experiment_tracker_sdk.client.instances import (
    ExperimentInstance,
    ProjectInstance,
    TeamInstance,
)


@dataclass(frozen=True)
class ExperimentInitResult:
    """Resolved team, project, and experiment instances for an initialized run.

    Args:
        experiment: Resolved or created experiment instance.
        project: Resolved or created project instance.
        team: Resolved or created team instance, if a team was requested.
    """

    experiment: ExperimentInstance
    project: ProjectInstance
    team: TeamInstance | None = None
