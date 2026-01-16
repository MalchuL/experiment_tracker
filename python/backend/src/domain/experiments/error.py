class ExperimentError(Exception):
    pass


class ExperimentNameParseError(ExperimentError):
    """Error raised when a experiment name does not match the pattern."""

    pass


class ExperimentNotAccessibleError(ExperimentError):
    """Error raised when a experiment is not accessible."""

    pass
