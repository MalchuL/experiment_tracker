class ProjectMemberError(Exception):
    """Base error for project member operations."""


class ProjectMemberAccessDenied(ProjectMemberError):
    """Caller cannot perform this member operation."""


class ProjectMemberNotFound(ProjectMemberError):
    """User or project not found for member operation."""


class ProjectMemberInvalidRole(ProjectMemberError):
    """Requested role is not allowed for invites or updates."""


class ProjectMemberLastEditor(ProjectMemberError):
    """Cannot remove the last user with project edit access (personal projects)."""
