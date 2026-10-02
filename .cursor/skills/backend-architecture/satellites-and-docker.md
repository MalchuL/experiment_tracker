# Satellite clients and Docker (backend)

## Satellite client layout

```
src/clients/<service>/
├── __init__.py          # re-export client + key DTOs/protocols
├── client.py            # HTTP implementation
├── dto.py               # request/response models for that service
└── protocol.py          # Typing.Protocol used by DI and tests
```

Optional legacy shim: `src/clients/<service>_client.py` that re-exports the package (avoid for new code).

### Client implementation

- Central `ENDPOINTS` dict (path templates).
- One private `_request` helper (method, path, params/json, error mapping).
- Validate responses with Pydantic (`model_validate`).
- Timeouts and base URL from settings (`get_settings().*_service_url`).
- For uploads/downloads, keep a small transfer strategy (multipart/stream) rather than ad-hoc files in every method.

### Protocol + NoOp

```python
class ExampleSatelliteClientProtocol(Protocol):
    async def get_items(self, project_id: str) -> ItemsDTO: ...

class NoOpExampleSatelliteClient:
    async def get_items(self, project_id: str) -> ItemsDTO:
        return ItemsDTO(data=[], total=0)
```

In `service_dependencies.py`:

- If settings URL is empty/missing → return NoOp (or domain NoOp service).
- Else → construct real client with that base URL.

Domain services depend on the **protocol** (or a domain-level facade protocol), never import the concrete client type in business logic if avoidable.

### Domain facade

`domain/<feature>/service.py` should:

1. Enforce RBAC / resource access.
2. Resolve local IDs (project, experiment, …) from Postgres when needed.
3. Call the satellite client.
4. Map satellite errors into domain errors when the user must see a clean failure.

Admin/lifecycle paths that intentionally skip user checks must be documented; the **caller** (admin route) enforces the admin key.

### Tolerant teardown

When deleting a primary resource, optional satellite cleanup should often use a helper that records success/skip/failure per step instead of failing the whole request when a secondary store is down. Return a structured cleanup DTO to the client when partial success is possible.

## Settings relevant to satellites

| Setting | Purpose |
|---------|---------|
| `*_SERVICE_URL` | Base URL for outbound client; empty → NoOp |
| `ALLOWED_ORIGINS` | CORS for browser clients of **this** API |
| `DATABASE_URL` | Primary relational store |
| `ADMIN_PANEL_KEY` | Separate ops channel header |

Local template: package `.env.example`. Compose overrides hosts to Docker DNS (`http://scalars:8001/api`, etc.).

## Docker

Multi-stage pattern with **uv**:

1. **Builder**: copy package (+ shared libs if path deps), `uv sync --frozen --no-dev`.
2. **Runtime**: copy venv/app, install minimal OS deps (e.g. `libpq`), `ENTRYPOINT` → uvicorn.
3. **Healthcheck**: `GET /openapi.json` or `/health` on the container port.

Entrypoint example:

```bash
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Build context is usually the **monorepo root** when the backend depends on a sibling shared package.

Pass secrets and URLs at **container runtime** via Compose `environment:` / `.env` — do not bake `JWT_SECRET` or DB passwords into the image.

### Compose checklist

- `DATABASE_URL` uses the Postgres **service hostname**, not `localhost`.
- Satellite URLs use Compose DNS.
- `ALLOWED_ORIGINS` lists the **UI** origin(s) the browser will send.
- Recreate the backend container after env changes; rebuild only when code/deps change.
