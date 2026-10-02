---
name: backend-architecture
description: Organize a FastAPI backend with DDD domain slices (controller, service, repository, dto, mapper, error), central DI, camelCase DTOs, async SQLAlchemy + Alembic, RBAC, satellite HTTP clients with Protocol/NoOp, pagination, uv, and Docker. Use when adding or changing API routes, domain logic, persistence, authz, outbound clients, settings, migrations, or backend tests.
---

# Backend architecture

Apply this layout and layering for FastAPI backends (uv, async SQLAlchemy). Do not invent parallel layers (fat controllers, repositories that raise `HTTPException`, or globals that bypass DI).

## Layout (where files live)

```
python/backend/                # or equivalent API package root
├── alembic/                   # migrations (outside src)
├── alembic.ini
├── Dockerfile
├── docker-entrypoint.sh
├── .env.example
├── pyproject.toml             # package-dir = src; pytest pythonpath = src
├── tests/                     # mirrors domain / api / clients
└── src/
    ├── api/                   # app factory, aggregator routes, auth/admin/health
    │   ├── main.py
    │   ├── error_logging.py
    │   └── routes/            # api.py aggregator + service_dependencies.py
    ├── config/                # Settings (BaseSettings)
    ├── db/                    # engine, session, URL helpers
    ├── clients/               # outbound HTTP to satellite services
    ├── domain/                # bounded contexts (DDD)
    ├── lib/                   # shared infra (pagination, dto_config, base repo)
    └── models.py              # centralized SQLAlchemy ORM models
```

Imports are top-level from `src/` (`api.main`, `domain.*`, `lib.*`). Use **uv** for sync/run/tests.

## DDD: `src/domain/<context>/`

One folder per bounded context. Create only the slices you need:

| File | Role |
|------|------|
| `controller.py` | FastAPI `APIRouter`; thin HTTP; map domain errors → `HTTPException` |
| `service.py` | Use-cases; RBAC; `commit`/`rollback`; orchestrate repos + clients |
| `repository.py` | Persistence; extends shared `BaseRepository[Model]` |
| `dto.py` | Pydantic request/response models |
| `mapper.py` | ORM ↔ DTO (keep ORM out of response models) |
| `error.py` | Domain exception hierarchy (plain `Exception` subclasses) |
| `protocol.py` / `noop_service.py` | Optional: swappable satellite-backed implementations |

**Variants**

- **Relational slice**: controller + service + repository + dto + mapper + error.
- **Satellite-backed** (no local tables): controller + service (+ protocol/noop); talk via `clients/`.
- **Nested subdomain**: `domain/<parent>/<child>/` with its own controller/service when the parent grows.
- **AuthZ-only domain**: permissions/deps/wrapper without an HTTP controller.

**Rules**

- Controllers never run SQL or call satellite HTTP clients directly.
- Services own transactions (`commit` / `rollback`); repositories mutate, do not commit by default.
- Repositories never raise FastAPI/`HTTPException`.
- Domain errors stay framework-free; controllers translate them (often **404** for “not accessible” to avoid leaking existence).

## Layer interaction

```text
Controller  →  Service  →  Repository (Advanced Alchemy)
    ↑              ↓
 HTTPException   Mapper: ORM ↔ DTO
 / response_model
```

| Layer | Responsibility |
|-------|----------------|
| **Controller** | Auth `Depends`, parse Query/Body, call service, translate domain errors → `HTTPException`, declare `response_model` |
| **Service** | RBAC, use-case flow, call repository/clients, use mapper, `commit`/`rollback` |
| **Repository** | Filters, ordering, eager loads, pagination via `ListOptions` → Alchemy `LimitOffset` |
| **Mapper** | Explicit ORM → DTO, CreateDTO → ORM, UpdateDTO → partial snake_case dict |

Controllers return **DTOs** (or `PaginatedResponse`), never ORM instances. Services raise domain errors; only controllers map them to HTTP.

Full code recipes: [layers-dto-pagination.md](layers-dto-pagination.md).

## Routes and app factory

1. Domain router declares its own `prefix` and `tags` (`APIRouter(prefix="/examples", …)`).
2. Aggregator `api/routes/api.py` `include_router`s every domain + system routes (health, auth, admin).
3. `create_app()` in `api/main.py`: CORS from settings, `include_router(api_router, prefix=settings.api_prefix)`, register exception handlers, lifespan (DB init / startup checks).

Final path ≈ `{api_prefix}{router.prefix}{route}`.

Optional: attach shared `dependencies=[…]` on a whole router (e.g. require auth for a nested resource).

## Dependency injection

Centralize wiring in `api/routes/service_dependencies.py` (or equivalent):

```
get_async_session → get_*_repository → get_*_service
                 ↘ get_permission_checker
                 ↘ get_*_client / NoOp when URL unset
```

Controllers only `Depends(get_example_service)`, `Depends(get_current_user)`, etc. Do not construct services inside route handlers.

Inject **protocols** for satellites so tests and “URL missing” boots can swap NoOps.

## DTOs (camelCase for the frontend)

Shared config — every public DTO sets `model_config = model_config()`:

```python
# lib/dto_config.py
from pydantic import ConfigDict, AliasGenerator
from pydantic.alias_generators import to_camel

def model_config() -> ConfigDict:
    return ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=to_camel,
            serialization_alias=to_camel,
        ),
        extra="forbid",
        populate_by_name=True,
    )
```

| In code (Python) | On the wire (JSON / OpenAPI) |
|------------------|------------------------------|
| `project_id` | `projectId` |
| `created_at` | `createdAt` |
| `display_name` | `displayName` |

- Declare fields in **snake_case**; clients send/receive **camelCase**.
- `populate_by_name=True` lets in-process code still validate with snake_case keys.
- Naming: `ExampleCreateDTO`, `ExampleUpdateDTO`, `ExampleDTO`; list envelope subclasses `PaginatedResponse[ExampleDTO]`.
- Query params: camelCase (`projectId: UUID`) or `Query(..., alias="projectId")`.
- Align `Field(max_length=…)` with shared entity limits when a shared package exists.

### Mapper + DtoConverter

```python
class ExampleMapper:
    def to_dto(self, row: Example) -> ExampleDTO: ...
    def from_create_dto(self, dto: ExampleCreateDTO) -> Example: ...
    def to_update_dict(self, dto: ExampleUpdateDTO) -> dict:
        return DtoConverter(ExampleUpdateDTO).dto_to_partial_dict_with_dto_case(dto)
        # exclude_unset=True, keys in snake_case for repository.update(**kwargs)
```

Never return SQLAlchemy models from controllers. See [layers-dto-pagination.md](layers-dto-pagination.md) for full DTO/mapper samples.

## Pagination (required pattern)

| Type | Layer | Role |
|------|-------|------|
| `ListOptions(limit, offset)` | controller → service → repo | Cap `limit` (e.g. max 100); never pass Alchemy types upward |
| `Page[T]` | repository → service | ORM rows + `has_next` + `total`; `.map(to_dto)` |
| `PaginatedResponse[T]` | service → HTTP | `{ data, hasNext, size, total }` via `model_config()` |

**Flow**

1. Controller: `limit`/`offset` Query → `ListOptions(limit=…, offset=…)`.
2. Service: after RBAC, `repo.list_*(…, list_options=…)`.
3. Repository (`BaseRepository.list`): with `list_options`, append Advanced Alchemy `LimitOffset`, call `list_and_count`, set `has_next = offset + len(data) < total`.
4. Service: `PaginatedResponse.from_page(page.map(mapper.to_dto))`.

Prefer DB-side pagination. Use `paginate_sequence` only for already-materialized lists. Full recipe: [layers-dto-pagination.md](layers-dto-pagination.md).

## Persistence (Advanced Alchemy)

- **Async** SQLAlchemy engine + `async_sessionmaker`; `get_async_session` yields a request-scoped session.
- Normalize DB URLs (e.g. `postgres://` → `postgresql+asyncpg://`).
- Central `models.py`; domains import models.
- Relationships: prefer `lazy="raise"`; pass `load=` (`selectinload`, …) in repository queries.
- Shared **`BaseRepository[Model]`** wraps Advanced Alchemy `SQLAlchemyAsyncRepository` with **`auto_commit=False`**:
  - `create` / `get_by_id` / `update` / `list` / `upsert`
  - `list(..., list_options=)` → Alchemy `LimitOffset` + `list_and_count` → `Page`
  - `delete` via Core `DELETE` by PK (avoids ORM identity / `lazy="raise"` graph issues)
  - Map Alchemy `NotFoundError` → `DBNotFoundError` for the service layer
- **Services** call `await self.db.commit()` / `rollback()` (or repo helpers that delegate to the session).
- **Alembic** at package root; async `env.py`; dated revisions.
- Hard deletes + FK `ON DELETE` unless the product already uses soft delete.

## Auth and authorization

### End-user auth

- JWT (and optional personal access tokens) via a dual “current user” dependency.
- If PATs exist: enforce token **scopes** that align with RBAC action strings; JWT can ignore scopes.
- Reject sensitive account ops (e.g. password change) when the caller is a PAT, if that is the product rule.

### RBAC

- Action string constants (e.g. `examples.view`, `examples.edit`) and role → permission maps under `domain/rbac/`.
- `PermissionService.has_permission` with clear inheritance rules (e.g. resource-scoped rows override parent/team).
- `PermissionChecker` facade (`can_*` helpers) injected into services; variants for **active superuser allow-all** and **inactive deny-all**.

### Separate ops/admin channel

Admin/bootstrap HTTP routes use a shared secret header (e.g. `X-Admin-Key`) with constant-time compare — **not** the end-user JWT flow. Log on startup whether the default insecure key is still in use **without printing the secret**.

## Domain errors → HTTP

```text
repository / service  →  raise ExampleNotAccessibleError
controller            →  HTTPException(404 or 400, detail=…)
```

Global handlers (`api/error_logging.py`): log + JSON for `HTTPException`, validation `422`, unhandled → generic `500` (no internal leak). Toggle stacktraces via settings.

## Satellite HTTP clients

One package per outbound service under `src/clients/<name>/`:

| File | Role |
|------|------|
| `client.py` | httpx (or similar); `ENDPOINTS` map; `_request` + DTO validate |
| `dto.py` | Wire models for that service |
| `protocol.py` | `Typing.Protocol` for DI/tests |
| NoOp impl | Empty/success-shaped responses when URL unset |

Domain **facade** services add authz and orchestration; they depend on the protocol, not a concrete client.

Empty satellite base URL in settings → wire NoOp in DI so the API still boots. Optional teardown helpers should tolerate satellite failures without always failing the primary DB delete (structured partial results).

More detail: [satellites-and-docker.md](satellites-and-docker.md).

## Settings / env

`config/settings.py`: Pydantic `BaseSettings` + `.env`; cached `get_settings()`.

Typical fields: `api_prefix`, `database_url`, `jwt_secret`, `allowed_origins`, satellite URLs, `log_level`, `admin_panel_key`.

Document in `.env.example`. Feature-toggle optional satellites by **URL presence**, not a second flag system, unless you need finer control.

## Testing

- Mirror source: `tests/domain/<slice>/test_{controller,service,repository,dto,mapper}.py`, plus `tests/api/`, `tests/clients/`.
- Shared `conftest.py`: in-memory SQLite (or test DB), session fixtures, permission fixtures, NoOp satellites.
- `pytest-asyncio` auto mode; `pythonpath = ["src"]`.
- Prefer layer-focused tests; controller tests cover HTTP mapping of domain errors.

## Run and Docker

```bash
# from the backend package root
uv sync
uv run uvicorn api.main:app --reload --port 8000 --log-level debug
uv run pytest
uv run alembic upgrade head
```

Docker: multi-stage **uv** image; entrypoint runs `uvicorn api.main:app --host 0.0.0.0 --port 8000`; healthcheck against OpenAPI or `/health`. Compose passes `DATABASE_URL`, secrets, satellite URLs, and `ALLOWED_ORIGINS` at **runtime**.

See [satellites-and-docker.md](satellites-and-docker.md).

## Adding a feature (checklist)

```
- [ ] Domain folder (error → dto → mapper → repository → service → controller)
- [ ] Register router + wire get_* in service_dependencies.py
- [ ] DTOs: model_config() camelCase; mapper ORM↔DTO; PATCH via dto_to_partial_dict_with_dto_case
- [ ] Controller → service → repository only; controller maps domain errors → HTTP
- [ ] Lists: ListOptions → BaseRepository.list(list_options=) → Page.map → PaginatedResponse
- [ ] RBAC in the service; commits in the service (Advanced Alchemy auto_commit=False)
- [ ] Alembic revision if schema changes; tests under tests/domain/<context>/
- [ ] Satellite work via clients/ + Protocol; NoOp when URL unset
```

More code: [layers-dto-pagination.md](layers-dto-pagination.md) · satellites: [satellites-and-docker.md](satellites-and-docker.md)

## Anti-patterns

- SQL or httpx inside controllers
- `HTTPException` raised from repositories or deep domain helpers
- Returning ORM models as response bodies
- Constructing services/repos outside DI
- Snake_case JSON on the public API (use `model_config()` / `to_camel`)
- Exposing Advanced Alchemy `LimitOffset` outside repositories (use `ListOptions`)
- Loading all rows then slicing in Python when the DB can paginate
- Committing inside repositories while services also commit
- ORM `session.delete` on graphs with `lazy="raise"` (prefer Core `DELETE` by id)
- Browser-facing secrets or admin keys logged in plaintext
- Requiring satellites to be up for the main API to import/boot
- Soft-delete columns invented without an existing product convention
