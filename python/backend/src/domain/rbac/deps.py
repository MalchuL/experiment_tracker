from sqlalchemy.ext.asyncio import AsyncSession

from domain.rbac.service import PermissionService
from domain.rbac.wrapper import (
    InactiveUserPermissionChecker,
    PermissionChecker,
    SuperuserPermissionChecker,
)
from models import User


def build_permission_checker(
    user: User,
    session: AsyncSession,
    permission_service: PermissionService,
) -> PermissionChecker:
    """Return a checker for inactive (deny all) or superuser (allow all) users."""
    if not user.is_active:
        return InactiveUserPermissionChecker(session, permission_service)
    if user.is_superuser:
        return SuperuserPermissionChecker(session, permission_service)
    return PermissionChecker(session, permission_service)
