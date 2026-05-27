# Teams

Teams group users and let projects inherit access from a shared membership list. A project may be standalone or owned by a team.

## Team fields

| Field | Meaning |
|-------|---------|
| `id` | Stable team id. |
| `name` | Team display name. |
| `description` | Optional context for the team. |
| `ownerId` | User who owns the team. |
| `createdAt` | Creation timestamp. |

The team list includes `canCreateProject` so the UI can show whether the current user can create projects inside each team.

## Roles

Roles are ordered by capability:

| Role | Typical use |
|------|-------------|
| `owner` | Team owner; represented as a synthetic owner row in member lists. |
| `admin` | Can manage team and higher-level resources granted by permissions. |
| `member` | Contributor-level access. |
| `viewer` | Read-oriented access. |

Managers cannot assign a role equal to or higher than their own role. Owners cannot be removed through membership operations. Admin removal and demotion are deliberately restricted.

## Members

Team members are managed by active user email lookup:

1. Look up a user by email in the team.
2. Add the user with a role.
3. Update role when needed.
4. Remove the member or let them leave the team.

The member list includes the owner plus non-owner members with email, display name, role, and ownership flag.

## Team-owned projects

When a project is created under a team:

- The project owner is inherited from the team owner.
- Team members can receive project access through team permissions.
- Project member rows can override team-inherited access for a specific project.

Deleting a team also deletes team-owned projects. The backend performs project cleanup first: experiment artifacts, at-step artifacts, scalar rows/tables, project artifacts, snapshots, and project rows are cleaned before the team row is removed.

## CLI

```bash
experiment-tracker team list
experiment-tracker team get <team-id>
experiment-tracker team create --name "Research" --description "Research team"
experiment-tracker team update <team-id> --name "Research"
experiment-tracker team delete <team-id> -y
```

## Related

- [Users](/docs/domains/users)
- [Projects: members](/docs/domains/projects#members)
- [SDK CLI](/docs/sdk/cli#teams)
