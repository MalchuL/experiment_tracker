from .roles import TeamRole
from .rights import Rights


def role_to_rights(role: TeamRole) -> Rights:
    match role:
        case TeamRole.OWNER:
            return Rights(
                name="owner",
                can_create_project=True,
                can_edit_project=True,
                can_delete_project=True,
                can_view_project=True,
                can_create_experiment=True,
                can_edit_experiment=True,
                can_delete_experiment=True,
                can_view_experiment=True,
                can_create_hypothesis=True,
                can_edit_hypothesis=True,
                can_delete_hypothesis=True,
                can_view_hypothesis=True,
                can_edit_team=True,
                can_view_team=True,
            )
        case TeamRole.ADMIN:
            return Rights(
                name="admin",
                can_create_project=True,
                can_edit_project=True,
                can_delete_project=True,
                can_view_project=True,
                can_create_experiment=True,
                can_edit_experiment=True,
                can_delete_experiment=True,
                can_view_experiment=True,
                can_create_hypothesis=True,
                can_edit_hypothesis=True,
                can_delete_hypothesis=True,
                can_view_hypothesis=True,
                can_edit_team=True,
                can_view_team=True,
            )
        case TeamRole.MEMBER:
            return Rights(
                name="member",
                can_create_project=False,
                can_edit_project=False,
                can_delete_project=False,
                can_view_project=True,
                can_create_experiment=True,
                can_edit_experiment=True,
                can_delete_experiment=True,
                can_view_experiment=True,
                can_create_hypothesis=True,
                can_edit_hypothesis=True,
                can_delete_hypothesis=True,
                can_view_hypothesis=True,
                can_edit_team=False,
                can_view_team=True,
            )
        case TeamRole.VIEWER:
            return Rights(
                name="viewer",
                can_create_project=False,
                can_edit_project=False,
                can_delete_project=False,
                can_view_project=True,
                can_create_experiment=False,
                can_edit_experiment=False,
                can_delete_experiment=False,
                can_view_experiment=True,
                can_create_hypothesis=False,
                can_edit_hypothesis=False,
                can_delete_hypothesis=False,
                can_view_hypothesis=True,
                can_edit_team=False,
                can_view_team=True,
            )
