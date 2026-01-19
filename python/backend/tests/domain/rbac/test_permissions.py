import pytest

from models import Role
from domain.rbac.permissions.team import (
    TeamActions,
    role_to_team_permissions as team_role_to_permissions,
)
from domain.rbac.permissions.project import (
    ProjectActions,
    role_to_project_permissions as project_role_to_permissions,
)


def _action_values(action_class: type) -> set[str]:
    return {value for name, value in vars(action_class).items() if name.isupper()}


@pytest.mark.parametrize("role", list(Role))
def test_team_permissions_include_all_actions(role: Role) -> None:
    expected_actions = _action_values(TeamActions)
    permissions = team_role_to_permissions(role)

    assert set(permissions.keys()) == expected_actions
    assert all(isinstance(value, bool) for value in permissions.values())


@pytest.mark.parametrize("role", list(Role))
def test_project_permissions_include_all_actions(role: Role) -> None:
    expected_actions = _action_values(ProjectActions)
    permissions = project_role_to_permissions(role)

    assert set(permissions.keys()) == expected_actions
    assert all(isinstance(value, bool) for value in permissions.values())
