from __future__ import annotations

from experiment_tracker_sdk.error import ExpTrackerError


class ExperimentInitError(ExpTrackerError):
    """Base error for experiment initialization strategy failures."""


class ProjectAmbiguousError(ExperimentInitError):
    """Raised when multiple projects match the requested name or ID."""


class ProjectNotFoundError(ExperimentInitError):
    """Raised when the requested project is not found."""


class ExperimentAmbiguousError(ExperimentInitError):
    """Raised when multiple experiments match the requested name or ID."""


class ExperimentNotFoundError(ExperimentInitError):
    """Raised when the requested experiment is not found."""


class TeamAmbiguousError(ExperimentInitError):
    """Raised when multiple teams match the requested name or ID."""


class TeamNotFoundError(ExperimentInitError):
    """Raised when the requested team is not found."""


class MultipleItemsResolveError(ExperimentInitError):
    """Raised when multiple matches cannot be resolved with the selected strategy."""
