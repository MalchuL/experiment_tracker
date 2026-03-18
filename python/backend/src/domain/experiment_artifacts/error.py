class ExperimentArtifactsNotAccessibleError(Exception):
    """Raised when a user cannot access experiment artifacts for a project."""


class ExperimentArtifactNotFoundError(Exception):
    """Raised when an experiment artifact cannot be found."""
