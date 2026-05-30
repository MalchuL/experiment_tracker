# Users

Users are the identity layer for the tracker. A user can sign in to the web UI, own teams and projects, receive direct project access, inherit access through teams, and create personal API tokens for the SDK.

## Profile

The public user shape contains:

| Field | Meaning |
|-------|---------|
| `id` | Stable user id. |
| `email` | Login email and lookup key for membership changes. |
| `displayName` | Optional human-friendly name. |
| `avatarUrl` | Optional profile image URL. |
| `createdAt` | Account creation timestamp. |

The current profile is available through `GET /users/me/profile`. The web UI uses the profile page for account details and password changes.

## Passwords

Users can change their own password with `POST /users/me/change-password` using:

- `currentPassword`
- `newPassword`

The new password must be at least 8 characters. Password changes require JWT/session authentication; they are intentionally blocked when the caller is authenticated with a personal API token.

## API tokens

Personal API tokens let training jobs, SDK scripts, and CLI commands call the backend without a browser session.

Token fields include:

- `name`
- `description`
- `scopes`
- `expiresAt`
- `revoked`
- `lastUsedAt`

The raw token value is returned only once when the token is created. Store it in your local SDK config or secret manager.

```bash
experiment-tracker init --base-url http://127.0.0.1:8000 --api-token <TOKEN>
experiment-tracker whoami
```

:::warning
Rotate a token immediately if it was copied into logs, committed, or shared outside the intended environment.
:::

## Access model

A user can access a project through:

- **Direct project permissions**: explicit project member rows.
- **Team inheritance**: membership in the team that owns the project.
- **Project override**: project-specific permissions written for a team member.
- **Ownership**: project or team owners have full control over their own resources.

User lookup for teams and projects is email-based and only returns active users.

## Superuser

A user with **`is_superuser`** set bypasses per-action RBAC checks in the backend `PermissionChecker` after a normal login. Superuser does **not** grant access to the bootstrap admin UI or admin HTTP routes.

Inactive accounts are denied before superuser is considered: deactivated users fail all permission checks even if they remain superusers in the database.

Operators can set **`is_superuser`** and **`is_active`** from the bootstrap [Admin panel](/docs/reference/admin-panel) (`/admin`), not from the regular profile page.

## Related

- [Admin panel](/docs/reference/admin-panel)
- [Teams](/docs/domains/teams)
- [Projects: members](/docs/domains/projects#members)
- [SDK CLI](/docs/sdk/cli)
