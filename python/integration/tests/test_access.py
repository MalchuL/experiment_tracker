import httpx
import pytest

from conftest import call


def test_profile_password_and_bad_credentials(api, user):
    """Persist profile edits and accept only valid password changes and logins."""
    updated = call(
        api, "PATCH", "users/me", json={"displayName": "Integration Researcher"}
    )
    assert updated["displayName"] == "Integration Researcher"
    assert call(api, "GET", "users/me")["displayName"] == "Integration Researcher"
    call(
        api,
        "POST",
        "users/me/change-password",
        status=400,
        json={
            "currentPassword": "wrong-password",
            "newPassword": "Changed-password-123!",
        },
    )
    call(
        api,
        "POST",
        "users/me/change-password",
        status=422,
        json={"currentPassword": user["password"], "newPassword": "short"},
    )
    call(
        api,
        "POST",
        "users/me/change-password",
        json={
            "currentPassword": user["password"],
            "newPassword": "Changed-password-123!",
        },
    )
    call(
        api,
        "POST",
        "auth/jwt/login",
        status=400,
        data={"username": user["email"], "password": user["password"]},
    )
    assert call(
        api,
        "POST",
        "auth/jwt/login",
        data={"username": user["email"], "password": "Changed-password-123!"},
    )["access_token"]


def test_pat_scope_and_revocation(api, project):
    """Enforce a PAT's read-only scope and reject it after use and revocation."""
    token = call(
        api,
        "POST",
        "users/me/api-tokens",
        json={"name": "Read only", "scopes": ["project.view"]},
    )
    with httpx.Client(
        base_url=str(api.base_url),
        headers={"Authorization": f"Bearer {token['token']}"},
        trust_env=False,
    ) as pat:
        assert call(pat, "GET", f"projects/{project['id']}")["id"] == project["id"]
        call(
            pat,
            "PATCH",
            f"projects/{project['id']}",
            status=403,
            json={"name": "Forbidden"},
        )
        revoked = call(api, "DELETE", f"users/me/api-tokens/{token['id']}")
        assert revoked["revoked"] is True
        assert (
            next(
                row
                for row in call(api, "GET", "users/me/api-tokens")["data"]
                if row["id"] == token["id"]
            )["revoked"]
            is True
        )
        call(pat, "GET", f"projects/{project['id']}", status=401)


def test_unused_revoked_pat_is_rejected(api, project):
    """Reject a revoked PAT even when it was never used before revocation."""
    token = call(
        api,
        "POST",
        "users/me/api-tokens",
        json={"name": "Unused", "scopes": ["project.view"]},
    )
    call(api, "DELETE", f"users/me/api-tokens/{token['id']}")
    response = api.get(
        f"projects/{project['id']}",
        headers={"Authorization": f"Bearer {token['token']}"},
    )
    assert response.status_code == 401, response.text


def test_inactive_user_pat_cannot_read_profile(api, admin, user):
    """Deny profile access through a PAT belonging to a deactivated user."""
    token = call(
        api, "POST", "users/me/api-tokens", json={"name": "Profile", "scopes": []}
    )
    call(admin, "PATCH", f"admin/users/{user['id']}", json={"isActive": False})
    response = api.get(
        "users/me/profile", headers={"Authorization": f"Bearer {token['token']}"}
    )
    assert response.status_code in (401, 403), response.text


def test_team_inheritance_override_and_direct_invite(api, user, make_user):
    """Apply project role overrides, restore team inheritance, and revoke invites."""
    member = make_user()
    outsider = make_user()
    team = call(api, "POST", "teams", json={"name": "Integration Team"})
    call(
        api,
        "POST",
        "teams/members",
        json={"teamId": team["id"], "userId": member["id"], "role": "member"},
    )
    assert (
        call(
            api,
            "GET",
            f"teams/{team['id']}/users/lookup",
            params={"email": member["email"]},
        )["id"]
        == member["id"]
    )
    project = call(
        api, "POST", "projects", json={"name": "Team project", "teamId": team["id"]}
    )
    path = f"projects/{project['id']}"
    assert call(member["client"], "GET", path)["id"] == project["id"]
    denied = outsider["client"].get(path)
    assert denied.status_code in (403, 404), denied.text
    rows = call(api, "GET", path + "/members")
    assert (
        next(row for row in rows if row["userId"] == member["id"])["accessSource"]
        == "team"
    )
    call(
        api, "PATCH", path + "/members", json={"userId": member["id"], "role": "viewer"}
    )
    rows = call(api, "GET", path + "/members")
    assert (
        next(row for row in rows if row["userId"] == member["id"])["accessSource"]
        == "override"
    )
    call(
        member["client"],
        "POST",
        "experiments",
        status=404,
        json={"projectId": project["id"], "name": "Denied"},
    )
    call(api, "DELETE", path + "/members", json={"userId": member["id"]})
    call(
        member["client"],
        "POST",
        "experiments",
        json={"projectId": project["id"], "name": "Inherited write"},
    )
    call(
        api,
        "POST",
        path + "/members",
        json={"email": outsider["email"], "role": "viewer"},
    )
    rows = call(api, "GET", path + "/members")
    assert (
        next(row for row in rows if row["userId"] == outsider["id"])["accessSource"]
        == "direct"
    )
    call(api, "DELETE", path + "/members", json={"userId": outsider["id"]})
    assert outsider["client"].get(path).status_code in (403, 404)
    call(
        api,
        "PATCH",
        "teams/members",
        json={"teamId": team["id"], "userId": member["id"], "role": "viewer"},
    )
    call(
        api,
        "DELETE",
        "teams/members",
        json={"teamId": team["id"], "userId": member["id"]},
    )
    assert member["client"].get(path).status_code in (403, 404)


@pytest.mark.parametrize(
    "path", ["projects", "teams", "experiments/recent", "users/me/api-tokens"]
)
def test_unauthenticated_access(api, path):
    """Require authentication for each protected collection endpoint."""
    assert api.get(path, headers={"Authorization": ""}).status_code == 401


def test_admin_key_search_password_and_superuser(admin, api, user, make_user):
    """Verify admin-key access, user search, password reset, and superuser checks."""
    call(api, "GET", "admin/users", status=403)
    users = call(admin, "GET", "admin/users", params={"q": user["email"], "limit": 1})
    assert users["total"] == 1 and users["items"][0]["id"] == user["id"]
    other = make_user()
    project = call(other["client"], "POST", "projects", json={"name": "Private"})
    assert api.get(f"projects/{project['id']}").status_code in (403, 404)
    call(
        admin,
        "PATCH",
        f"admin/users/{user['id']}",
        json={"displayName": "Admin edited", "isSuperuser": True},
    )
    assert call(api, "GET", f"projects/{project['id']}")["id"] == project["id"]
    password = call(admin, "POST", f"admin/users/{user['id']}/reset-password")[
        "temporaryPassword"
    ]
    call(
        api,
        "POST",
        "auth/jwt/login",
        data={"username": user["email"], "password": password},
    )
    call(admin, "PATCH", f"admin/users/{user['id']}", json={"isActive": False})
    assert api.get(f"projects/{project['id']}").status_code in (401, 403)
    for path, key in [
        ("admin/teams", "items"),
        ("admin/storage/buckets", "buckets"),
        ("admin/storage/scalars", "tables"),
    ]:
        result = call(admin, "GET", path, params={"limit": 1, "offset": 0})
        assert "total" in result and len(result[key]) <= 1
