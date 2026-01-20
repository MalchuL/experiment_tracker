from uuid import UUID
from domain.rbac.service import PermissionService
from domain.rbac.permissions import ProjectActions, TeamActions
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionChecker:
    """Convenience wrapper for common permission checks."""

    def __init__(self, db: AsyncSession):
        """Initialize with a permission service."""
        self.permission_service = PermissionService(db)

    # Project-scoped permissions
    async def can_edit_project(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can edit a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.EDIT_PROJECT,
        )

    async def can_delete_project(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can delete a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.DELETE_PROJECT,
        )

    async def can_view_project(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can view a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.VIEW_PROJECT,
        )

    async def can_create_experiment(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can create experiments in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.CREATE_EXPERIMENT,
        )

    async def can_edit_experiment(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can edit experiments in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.EDIT_EXPERIMENT,
        )

    async def can_delete_experiment(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can delete experiments in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.DELETE_EXPERIMENT,
        )

    async def can_view_experiment(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can view experiments in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.VIEW_EXPERIMENT,
        )

    async def can_create_hypothesis(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can create hypotheses in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.CREATE_HYPOTHESIS,
        )

    async def can_edit_hypothesis(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can edit hypotheses in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.EDIT_HYPOTHESIS,
        )

    async def can_delete_hypothesis(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can delete hypotheses in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.DELETE_HYPOTHESIS,
        )

    async def can_view_hypothesis(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can view hypotheses in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.VIEW_HYPOTHESIS,
        )

    async def can_create_metric(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can create metrics in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.CREATE_METRIC,
        )

    async def can_edit_metric(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can edit metrics in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.EDIT_METRIC,
        )

    async def can_delete_metric(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can delete metrics in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.DELETE_METRIC,
        )

    async def can_view_metric(self, user_id: UUID, project_id: UUID) -> bool:
        """Return whether the user can view metrics in a project."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            project_id=project_id,
            action=ProjectActions.VIEW_METRIC,
        )

    # Team-scoped permissions
    async def can_create_project(self, user_id: UUID, team_id: UUID) -> bool:
        """Return whether the user can create projects within a team."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            team_id=team_id,
            action=TeamActions.CREATE_PROJECT,
        )

    async def can_delete_team_project(self, user_id: UUID, team_id: UUID) -> bool:
        """Return whether the user can delete team projects."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            team_id=team_id,
            action=TeamActions.DELETE_PROJECT,
        )

    async def can_view_team_projects(self, user_id: UUID, team_id: UUID) -> bool:
        """Return whether the user can view team projects."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            team_id=team_id,
            action=TeamActions.VIEW_PROJECT,
        )

    async def can_manage_team(self, user_id: UUID, team_id: UUID) -> bool:
        """Return whether the user can manage the team."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            team_id=team_id,
            action=TeamActions.MANAGE_TEAM,
        )

    async def can_delete_team(self, user_id: UUID, team_id: UUID) -> bool:
        """Return whether the user can delete the team."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            team_id=team_id,
            action=TeamActions.DELETE_TEAM,
        )

    async def can_view_team(self, user_id: UUID, team_id: UUID) -> bool:
        """Return whether the user can view the team."""
        return await self.permission_service.has_permission(
            user_id=user_id,
            team_id=team_id,
            action=TeamActions.VIEW_TEAM,
        )
