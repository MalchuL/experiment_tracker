from experiment_tracker_sdk.error import ExpTrackerError


class RunnerError(ExpTrackerError):
    pass


class ProjectAmbiguousError(RunnerError):
    """Raised when multiple projects match the name or ID."""


class ProjectNotFoundError(RunnerError):
    """Raised when the project is not found."""


class ExperimentAmbiguousError(RunnerError):
    """Raised when multiple experiments match the name or ID."""


class ExperimentNotFoundError(RunnerError):
    """Raised when the experiment is not found."""


class TeamAmbiguousError(RunnerError):
    """Raised when multiple teams match the name or ID."""


class TeamNotFoundError(RunnerError):
    """Raised when the team is not found."""


class MultipleItemsResolveError(RunnerError):
    """Raised when multiple items match the name or ID."""
