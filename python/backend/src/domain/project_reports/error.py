class ReportNotFoundError(Exception):
    """Report row missing or wrong id."""


class ReportNotAccessibleError(Exception):
    """User lacks permission for this report or project."""
