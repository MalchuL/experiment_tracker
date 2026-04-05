class ExperimentArtifactsNotAccessibleError(Exception):
    """Raised when a user cannot access experiment artifacts for a project."""


class ExperimentArtifactNotFoundError(Exception):
    """Raised when an experiment artifact cannot be found."""


class ExperimentArtifactAmbiguousError(Exception):
    """Raised when multiple logged artifacts match the same step/name query."""
