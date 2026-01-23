class MetricError(Exception):
    pass


class MetricNotAccessibleError(MetricError):
    """Error raised when a metric is not accessible."""

    pass


class MetricNotFoundError(MetricError):
    """Error raised when a metric is not found."""

    pass
