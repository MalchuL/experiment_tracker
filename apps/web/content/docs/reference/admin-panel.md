# Admin panel

The **admin panel** is a separate bootstrap and operations surface for instance operators. It is **not** the same as marking a user as **superuser** in the database.

| Mechanism | How access works |
|-----------|------------------|
| **Admin panel** (`/admin`) | Shared secret: backend env `ADMIN_PANEL_KEY`, sent as HTTP header `X-Admin-Key`. No JWT or session required. |
| **Superuser** (`User.is_superuser`) | Normal login (JWT or session). Bypasses per-action RBAC in `PermissionChecker` only; does not unlock the admin UI or admin HTTP routes. |

:::danger
Anyone who knows `ADMIN_PANEL_KEY` can list all users and teams, reset passwords, edit accounts, and run storage admin actions. Use a long random value in production, restrict network access, and rotate the key if it leaks.
:::

## Configuration

Set on the **main API** (backend):

```bash
export ADMIN_PANEL_KEY="your-long-random-secret"
```

- Default for local dev is `admin`. The backend logs a **warning** on startup when the key is still the default.
- The admin HTTP API is mounted under `/api/admin` (with your configured API prefix).

The web UI reads the key from **`sessionStorage`** after you unlock `/admin` in the browser. It is not stored in cookies and is not tied to your logged-in user.

## Web UI

| URL | Purpose |
|-----|---------|
| [`/admin`](/admin) | Unlock with the admin key; browse and edit users; browse teams; reset passwords; delete inactive users. |
| [`/admin/storage`](/admin/storage) | Object-storage buckets and ClickHouse scalar tables (list, clear, reconcile, drop). |

### Users tab

Each row shows **email**, **display name**, **active**, and **superuser**. Edit fields inline, then click **Save** to apply changes via `PATCH /api/admin/users/{user_id}`.

Other actions per row:

- **Reset password** — generates a one-time temporary password in the API response; copy it immediately.
- **Delete** — only allowed when the user is **inactive**; removes personal projects (with satellite teardown) then the user row. Team-owned projects are not bulk-deleted.

Search and pagination use `q`, `limit` (default 20, max 100), and `offset`.

### Teams tab

Read-only catalog: team id, name, description, owner id, created time. Same pagination and search parameters as users.

## Superuser and inactive accounts

**Superuser** (`is_superuser: true`) affects permission checks after a normal login:

- `PermissionChecker` grants every `can_*` action when the user is active.
- Inactive users are denied first: inactive accounts always fail permission checks, even if they are superusers.
- Superuser does **not** expand project list visibility; it only bypasses per-action checks where `get_permission_checker` is used.

Grant or revoke superuser from the admin panel **Active / Superuser** fields (saved with **Save** via PATCH).

**Inactive** (`is_active: false`) users cannot sign in (FastAPI Users). With an existing session or API token, permission checks still deny all actions until the account is reactivated.

## HTTP API (admin key only)

All routes require header **`X-Admin-Key`** matching `ADMIN_PANEL_KEY`. Responses use camelCase JSON aliases where DTOs define them.

### Users and teams

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/users` | Paginated users; `q` filters email, display name, user id substring. |
| `GET` | `/admin/teams` | Paginated teams; `q` filters name and description. |
| `PATCH` | `/admin/users/{user_id}` | Update `email`, `displayName`, `isActive`, `isSuperuser` (partial body). |
| `POST` | `/admin/users/{user_id}/reset-password` | New random password; response includes `temporaryPassword` once. |
| `DELETE` | `/admin/users/{user_id}` | Delete user (must be inactive); optional `detailed=true` for teardown steps. |

Example (curl):

```bash
curl -sS -H "X-Admin-Key: $ADMIN_PANEL_KEY" \
  "http://127.0.0.1:8000/api/admin/users?limit=20&offset=0"
```

### Storage (proxied to satellite services)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/storage/buckets` | List object-storage buckets; optional `q`, `reconcile`. |
| `DELETE` | `/admin/storage/buckets/{bucket_id}` | Delete bucket metadata (and related cleanup per service rules). |
| `POST` | `/admin/storage/buckets/storage-only` | Create storage-only bucket. |
| `DELETE` | `/admin/storage/buckets/storage-only/clear` | Clear storage-only bucket contents. |
| `POST` | `/admin/storage/buckets/{bucket_id}/reconcile` | Reconcile bucket vs database. |
| `DELETE` | `/admin/storage/buckets/{bucket_id}/clear` | Clear bucket contents. |
| `GET` | `/admin/storage/scalars` | List ClickHouse scalar tables; optional `q`. |
| `DELETE` | `/admin/storage/scalars/{table_name}` | Drop a scalar storage table. |

Use **`/admin/storage`** in the web UI for the same operations with confirmation dialogs.

## Related

- [Users](/docs/domains/users) — profiles, password change (`POST /users/me/change-password`), and API tokens.
- [Architecture overview](/docs/architecture-overview) — how the API, scalars service, and object storage connect.
