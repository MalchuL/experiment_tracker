# Where to put your email (maintainer / fork)

This note lives under the repo root **`docs/`** folder (developer notes), not the in-app documentation under `apps/web/content/docs/`.

Use your real address only in **local or private** places. Tracked files in this repo use placeholders such as `email@mail.com` in package metadata so nothing personal is committed by default.

## Python packages (`pyproject.toml`)

Set **`[project].authors`** to your name and email if you publish or distribute wheels/sdists:

| Package | File |
|---------|------|
| SDK | `python/sdk/pyproject.toml` |
| Scalars service | `python/scalars_service/pyproject.toml` |
| Object storage | `python/object_storage/pyproject.toml` |

The main API package uses a team-style author line only; you may add an `email` field there if you want it on PyPI metadata: `python/backend/pyproject.toml`.

## Git commits

Your commit attribution is **not** stored in these files; configure Git locally:

```bash
git config user.email "you@example.com"
git config user.name "Your Name"
```

(Use `--global` if you want that identity for all repositories on the machine.)

## Product account (running app)

End-user **login email** and profile email are stored in the application database after you register or update your profile in the UI. They are not set via a static file in this repository.

## Optional repo conventions

If you add them later, common places for a **contact email** include `CODEOWNERS`, `SECURITY.md`, or the root `README.md`. None of those are required by this codebase today.
