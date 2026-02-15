class ScalarsError(Exception):
    """Base class for scalars errors."""

    pass


class ScalarsNotAccessibleError(ScalarsError):
    """Error raised when a scalars is not accessible."""

    pass
