class DBError(Exception):
    """Base class for database errors."""

    pass


class DBNotFoundError(DBError):
    """Error raised when a resource is not found."""

    pass


class DBAlreadyExistsError(DBError):
    """Error raised when a resource already exists."""

    pass


class DBInvalidOperationError(DBError):
    """Error raised when an invalid operation is performed."""

    pass
