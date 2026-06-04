class ExperimentDataNotAccessibleError(Exception):
    """Raised when a user cannot access experiment data for RBAC reasons.

    Args:
        *args: Human-readable details passed to ``Exception``.

    Result:
        Domain error translated to a 404 by the API to avoid leaking resource
        existence across project boundaries.
    """

    pass


class ExperimentDataStorageUnavailableError(Exception):
    """Raised when snapshot operations require unconfigured object storage.

    Args:
        *args: Human-readable details passed to ``Exception``.

    Result:
        Domain error translated to a 502 because the backing storage dependency
        is unavailable for this deployment.
    """

    pass


class ExperimentSnapshotNotFoundError(Exception):
    """Raised when an experiment has no snapshot metadata to read or delete.

    Args:
        *args: Human-readable details passed to ``Exception``.

    Result:
        Domain error translated to a 404 by the API.
    """

    pass
