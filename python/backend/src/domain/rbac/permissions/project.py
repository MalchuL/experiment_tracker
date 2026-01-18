from typing import Dict, Iterable

from models import TeamRole


class ProjectActions:
    # Current Project
    EDIT_PROJECT = "project.edit"
    DELETE_PROJECT = "project.delete"
    VIEW_PROJECT = "project.view"
    # Experiments
    CREATE_EXPERIMENT = "experiments.create"
    EDIT_EXPERIMENT = "experiments.edit"
    DELETE_EXPERIMENT = "experiments.delete"
    VIEW_EXPERIMENT = "experiments.view"
    # Hypotheses
    CREATE_HYPOTHESIS = "hypotheses.create"
    EDIT_HYPOTHESIS = "hypotheses.edit"
    DELETE_HYPOTHESIS = "hypotheses.delete"
    VIEW_HYPOTHESIS = "hypotheses.view"
    # Metrics
    CREATE_METRIC = "metrics.create"
    EDIT_METRIC = "metrics.edit"
    DELETE_METRIC = "metrics.delete"
    VIEW_METRIC = "metrics.view"


PROJECT_ACTIONS = (
    ProjectActions.EDIT_PROJECT,
    ProjectActions.DELETE_PROJECT,
    ProjectActions.VIEW_PROJECT,
    ProjectActions.CREATE_EXPERIMENT,
    ProjectActions.EDIT_EXPERIMENT,
    ProjectActions.DELETE_EXPERIMENT,
    ProjectActions.VIEW_EXPERIMENT,
    ProjectActions.CREATE_HYPOTHESIS,
    ProjectActions.EDIT_HYPOTHESIS,
    ProjectActions.DELETE_HYPOTHESIS,
    ProjectActions.VIEW_HYPOTHESIS,
    ProjectActions.CREATE_METRIC,
    ProjectActions.EDIT_METRIC,
    ProjectActions.DELETE_METRIC,
    ProjectActions.VIEW_METRIC,
)


def _build_permissions(allowed_actions: Iterable[str]) -> Dict[str, bool]:
    allowed_set = set(allowed_actions)
    return {action: action in allowed_set for action in PROJECT_ACTIONS}


def role_to_project_permissions(role: TeamRole) -> Dict[str, bool]:
    match role:
        case TeamRole.OWNER:
            return _build_permissions(PROJECT_ACTIONS)
        case TeamRole.ADMIN:
            return _build_permissions(PROJECT_ACTIONS)
        case TeamRole.MEMBER:
            allowed = set(PROJECT_ACTIONS) - {
                ProjectActions.EDIT_PROJECT,
                ProjectActions.DELETE_PROJECT,
            }
            return _build_permissions(allowed)
        case TeamRole.VIEWER:
            allowed = {
                ProjectActions.VIEW_PROJECT,
                ProjectActions.VIEW_EXPERIMENT,
                ProjectActions.VIEW_HYPOTHESIS,
                ProjectActions.VIEW_METRIC,
            }
            return _build_permissions(allowed)
