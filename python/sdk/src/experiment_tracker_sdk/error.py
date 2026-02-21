class ExpTrackerError(Exception):
    """Base class for all ExpTracker errors."""

    pass


class ExpTrackerConfigError(ExpTrackerError):
    """Error raised when the ExpTracker configuration is invalid."""

    pass


class ExpTrackerAPIError(ExpTrackerError):
    """Error raised when the ExpTracker API returns an error."""

    pass


class ExpTrackerProgressError(ExpTrackerError):
    """Error raised when the progress is invalid."""

    pass
