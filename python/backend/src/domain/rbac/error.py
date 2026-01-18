class RBACError(Exception):
    pass


class InvalidScopeError(RBACError):
    """Error raised when an invalid scope is provided."""

    pass


class InvalidIdError(RBACError):
    """Error raised when an invalid id is provided."""

    pass
