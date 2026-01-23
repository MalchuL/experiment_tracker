class HypothesisError(Exception):
    pass


class HypothesisNotAccessibleError(HypothesisError):
    """Error raised when a hypothesis is not accessible."""

    pass


class HypothesisNotFoundError(HypothesisError):
    """Error raised when a hypothesis is not found."""

    pass
