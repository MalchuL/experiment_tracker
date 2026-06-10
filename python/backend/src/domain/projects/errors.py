class ProjectNotAccessibleError(Exception):
    pass


class ProjectPermissionError(Exception):
    pass


class ProjectTransferError(Exception):
    """Raised when a project team or ownership transfer violates an invariant."""

    pass
