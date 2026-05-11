# Restoring lifecycle `is_active` (teams, projects, experiments)

This note was written from an analysis of **git staged** changes (index vs `HEAD`) in this repository. It maps what the lifecycle feature added so it can be reintroduced later, and flags follow-up areas (metrics, scalars, artifacts, experiment pickers).

**Important:** The same staged snapshot also contained **unrelated** work (for example admin storage UI, ClickHouse storage-size helpers, object storage bucket tests, scalars integration tests). When you restore **only** lifecycle/`is_active`, cherry-pick by file or re-apply hunks—do not assume every staged file belongs to this feature.

---

## Behaviour summary (what to bring back)

1. **PostgreSQL:** Boolean `is_active` on `teams`, `projects`, and `experiments` (default `true`, non-null).
2. **Listing / discovery:** Repositories default to **active-only** (`include_inactive=False`). Optional `include_inactive=True` for internal flows (for example loading a project with experiments before delete).
3. **HTTP API:**
   - **Deactivate / reactivate:** `POST …/deactivate` and `POST …/reactivate` for teams, projects, and experiments.
   - **Delete:** Hard delete of an experiment (and analogous rules for project/team) is only allowed when the entity is **inactive** (staged experiment delete returned `bool` and responded with `{"success": true}` on success).
4. **Admin (users):** Deactivate user, reactivate user, and delete user only when inactive (with copy in the admin UI about inactive users).
5. **DTOs / JSON:** Responses expose `isActive` (or `is_active` depending on mapper conventions) for team, project, and experiment payloads.
6. **Web UI:** “Danger zone” / lifecycle cards for team, project settings, and experiment details: deactivate, reactivate, delete (with confirmations). List surfaces show inactive state where implemented (for example project cards).

**Design gap to resolve when reimplementing:** `GET /experiments/{id}` used `get_experiment_if_accessible`, which in the staged code **rejected inactive** experiments. That makes a dedicated “inactive experiment” detail page awkward unless the client keeps cache, you add a separate endpoint, or you allow **view** (read-only) for inactive while still blocking edits—decide explicitly and align the danger-zone flow.

---

## 1. Database and ORM

| Place | What to restore |
|--------|------------------|
| `python/backend/alembic/versions/20260503_01_lifecycle_active_flags.py` | Adds `is_active` to `teams`, `projects`, `experiments` (with idempotent `_add_is_active`). **Same revision** also changes `projects.owner_id` / `teams.owner_id` to nullable with `ON DELETE SET NULL`. If you only want flags, split a new migration; if you keep this file, run `alembic upgrade head` after merge. |
| `python/backend/src/models.py` | `Mapped[bool] is_active` on `Team`, `Project`, and `Experiment` models (`default=True`, `nullable=False`). |

Downgrade in that migration drops `is_active` columns (and reverts owner FK behaviour)—keep in sync with production rollbacks.

---

## 2. Backend — experiments

| File | What to restore |
|------|------------------|
| `python/backend/src/domain/experiments/repository.py` | `include_inactive: bool = False` on `get_user_experiments`, `get_latest_experiments`, `get_experiments_by_project`, `get_experiments_by_ids`; append `Experiment.is_active.is_(True)` when `include_inactive` is false; `list_experiment_ids_for_project_by_created_at_desc` filters active only. |
| `python/backend/src/domain/experiments/service.py` | `get_experiment_if_accessible` / `update_experiment`: reject inactive where staged; `delete_experiment`: require inactive then satellites + DB delete; `set_experiment_active(user, id, is_active)`; adjust `get_experiment_usage` / helpers as in staged (e.g. `_ignore_missing` usage). |
| `python/backend/src/domain/experiments/controller.py` | `POST /{experiment_id}/deactivate`, `POST /{experiment_id}/reactivate`, `DELETE /{experiment_id}` wired to the above (staged delete returned simple success JSON). |
| `python/backend/src/domain/experiments/dto.py` | `is_active` / `isActive` on list/detail DTOs as in staged. |
| `python/backend/src/domain/experiments/mapper.py` | Map `is_active` between ORM and DTOs. |
| `python/backend/tests/domain/experiments/test_service.py` | Assertions for inactive experiments, deactivate/delete rules, etc. |

---

## 3. Backend — projects

| File | What to restore |
|------|------------------|
| `python/backend/src/domain/projects/repository.py` | `include_inactive` on project fetches; `Project.is_active.is_(True)` default filter; `get_by_id` / full load with `include_inactive` for delete flows. |
| `python/backend/src/domain/projects/service.py` | Hide inactive from normal access; `set_project_active`; delete only when project inactive; experiment counts using **active** experiments where staged did. |
| `python/backend/src/domain/projects/controller.py` | `POST /{project_id}/deactivate`, `POST /{project_id}/reactivate`, and any list/query params if present in staged diff. |
| `python/backend/src/domain/projects/dto.py`, `mapper.py` | `is_active` on project DTOs and mapping. |
| `python/backend/tests/domain/projects/test_service.py`, `test_controller.py` | Lifecycle tests. |

---

## 4. Backend — teams

| File | What to restore |
|------|------------------|
| `python/backend/src/domain/team/teams/repository.py` | Filter `Team.is_active.is_(True)` for member listings and team-by-id; `include_inactive` for delete/reactivate paths. |
| `python/backend/src/domain/team/teams/service.py` | `set_team_active`; delete team only when inactive; team loads with `include_inactive` where needed. |
| `python/backend/src/domain/team/teams/controller.py` | `POST /{team_id}/deactivate`, `POST /{team_id}/reactivate`. |
| `python/backend/src/domain/team/teams/dto.py`, `mapper.py` | `is_active` on read DTOs. |
| `python/backend/tests/domain/team/teams/test_service.py`, `test_controller.py` | Lifecycle tests. |

---

## 5. Backend — admin users

| File | What to restore |
|------|------------------|
| `python/backend/src/api/routes/admin.py` | `AdminUserRowDTO` includes `is_active`; deactivate sets `user.is_active = False`; `POST …/users/{user_id}/reactivate` sets active; delete user requires inactive (staged raised 400 if still active). |
| `python/backend/tests/api/test_admin_and_password.py` | Coverage for reactivate/deactivate/delete rules. |

Note: `User.is_active` for **auth users** already exists elsewhere (for example team member queries). Do not confuse with team/project/experiment `is_active`.

---

## 6. Backend — other touchpoints

| File | Why it matters |
|------|----------------|
| `python/backend/src/domain/scalars/service.py` | Staged index may not add `is_active` here, but `get_experiments_by_ids(..., include_inactive=False)` means **passing inactive experiment IDs** into scalar queries can yield “experiments not found”. Align product behaviour (see checklist below). |
| `python/backend/src/api/routes/service_dependencies.py` | Only if staged wiring changed experiment/project services (verify diff). |

---

## 7. Web app (`apps/web`)

| Area | Files (from staged set) |
|------|-------------------------|
| API route constants | `apps/web/src/lib/constants/api-routes.ts` — `DEACTIVATE` / `REACTIVATE` for teams, projects, experiments; admin `REACTIVATE_USER` / `DEACTIVATE_USER` / delete copy. |
| Types + normalisation | `apps/web/src/domain/experiments/types/types.ts`, `apps/web/src/domain/projects/types/types.ts`, `apps/web/src/domain/projects/utils/normalize-project.ts`, `apps/web/src/domain/teams/types.ts` — `isActive` fields. |
| Services | `experiments-service.ts`, `projects-service.ts`, `teams-service.ts` — `deactivate`, `reactivate`, and delete behaviour aligned with backend. |
| Hooks | `apps/web/src/domain/experiments/hooks/experiment-hook.ts` (if staged extended beyond baseline). |
| UI components | `experiment-danger-zone-card.tsx`, `project-danger-zone.tsx`, `team-danger-zone.tsx`; exports in `domain/*/components/index.ts`. |
| Pages | `projects/page.tsx`, `teams/[teamId]/page.tsx`, `projects/[projectId]/page.tsx`, `projects/[projectId]/settings/page.tsx`, `admin/page.tsx` — inactive badges, disabled actions, or admin messaging. |
| Experiment details | `experiment-details-view.tsx` — mount danger zone / lifecycle section. |

`apps/web/src/app/admin/storage/page.tsx` and `apps/web/src/lib/format-storage-usage.ts` were in the same staged list but are **storage admin**, not lifecycle.

---

## 8. Tests (backend)

Restore the staged test deltas under:

- `python/backend/tests/domain/experiments/test_service.py`
- `python/backend/tests/domain/projects/test_service.py`, `test_controller.py`
- `python/backend/tests/domain/team/teams/test_service.py`, `test_controller.py`
- `python/backend/tests/api/test_admin_and_password.py`

---

## 9. How to restore mechanically

1. **From git:** If the work still exists on a branch or commit, restore paths with `git checkout <ref> -- <path>` for each path in sections 1–8, then resolve conflicts with newer `main`.
2. **From patch:** `git show <commit>:path` or save `git diff <base> <tip>` for the lifecycle paths only and re-apply.
3. **Run migrations** after backend models match the revision.
4. **Run tests:** `cd python/backend && uv run pytest` for the touched suites; web lint/build as you normally do.

---

## 10. Checklist for a future implementer (read this)

### Experiment selection and downstream APIs

Inactive experiments are **hidden** from default repository lists and from `list_experiment_ids_for_project_by_created_at_desc`. Any code path that:

- builds **metric** queries,
- loads **scalars** or **last_logged** for chosen experiment IDs,
- lists or downloads **artifacts**,

must be checked for:

1. **Stale client state:** URL or local state still referencing an experiment id after deactivation; server may reject or omit it—avoid silent empty charts; show “experiment unavailable or deactivated”.
2. **Batch endpoints:** `get_experiments_by_ids` without `include_inactive` will drop inactive ids—confirm whether batch metric/scalar routes should allow inactive for auditors or deny like `GET /experiments/{id}`.
3. **Training / SDK:** Logging scalars or artifacts to a deactivated experiment should fail clearly (permission vs lifecycle vs 404)—align HTTP status and messages with RBAC docs.
4. **Project / team inactive:** Cascading expectations (can you view nested experiments if project inactive?) should match product; staged code filtered projects/teams in several queries—re-verify dashboard, project switcher, and BFF proxies.

### UX / API consistency

- Decide whether **inactive** entities are **readable** by editors (recommended for reactivate/delete flows) vs **fully hidden** (staged strict mode on `get_experiment_if_accessible`).
- Ensure **deactivate → delete** order is enforced server-side (not only in the UI).

---

## 11. Staged file list reference (lifecycle-related)

Use `git diff --cached --name-only` on your machine to reconcile with current branch state. The analysis that produced this document included at least:

**Backend:** `alembic/versions/20260503_01_lifecycle_active_flags.py`, `models.py`, `api/routes/admin.py`, `domain/experiments/*`, `domain/projects/*`, `domain/team/teams/*`, and matching `tests/**`.

**Web:** `api-routes.ts`, domain experiments/projects/teams (types, services, hooks, danger-zone components, pages listed above), `experiment-details-view.tsx`.

**Also staged but not lifecycle:** large portions of `python/scalars_service`, `python/object_storage`, `apps/web` admin storage, `AGENTS.md`, etc.—treat separately.

---

*Generated from staged-index review; filenames and behaviour describe the staged implementation as of the snapshot used for this write-up.*
