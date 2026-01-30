class ApiTokenError(Exception):
    """Base API token error."""


class ApiTokenNotFoundError(ApiTokenError):
    """Token not found."""


class ApiTokenRevokedError(ApiTokenError):
    """Token revoked."""


class ApiTokenExpiredError(ApiTokenError):
    """Token expired."""


class ApiTokenInvalidError(ApiTokenError):
    """Token invalid."""
