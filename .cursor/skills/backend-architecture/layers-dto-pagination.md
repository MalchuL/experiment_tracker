# Layers, DTOs, mappers, Advanced Alchemy, pagination

Generic recipes. Adapt names to the bounded context.

## Layer interaction

```text
HTTP request
  → controller   (auth deps, Query/Body → calls service, maps domain errors → HTTP)
    → service    (RBAC, use-case, mapper, commit/rollback)
      → repository (Advanced Alchemy / SQLAlchemy; returns ORM or Page[ORM])
    ← service    (map ORM → DTO / Page → PaginatedResponse)
  ← controller   (response_model = DTO; FastAPI serializes camelCase)
```

| Layer | May do | Must not |
|-------|--------|----------|
| Controller | `Depends`, validate query/body, call service, `HTTPException` | SQL, httpx, `session.commit`, build ORM |
| Service | RBAC, orchestrate repos/clients, map via mapper, `commit`/`rollback` | Raise `HTTPException`, touch `Request` |
| Repository | Filters, `list_and_count`, eager loads, Core `DELETE` | Commit (default), raise HTTP, return DTOs |
| Mapper | ORM ↔ DTO, partial update dicts | I/O, sessions, permissions |

### Controller (handles results / errors)

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from lib.pagination import MAX_LIST_PAGE_SIZE, ListOptions
from .dto import ExampleCreateDTO, ExampleDTO, ExampleListResponseDTO
from .error import ExampleNotAccessibleError, ExampleNotFoundError
from .service import ExampleService

router = APIRouter(prefix="/examples", tags=["examples"])

def _raise_http(error: Exception) -> None:
    if isinstance(error, ExampleNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, ExampleNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))

@router.get("", response_model=ExampleListResponseDTO)
async def list_examples(
    projectId: UUID,
    limit: int = Query(default=10, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
    service: ExampleService = Depends(get_example_service),
):
    return await service.list_for_project(
        user, projectId, ListOptions(limit=limit, offset=offset)
    )

@router.get("/{example_id}", response_model=ExampleDTO)
async def get_example(
    example_id: UUID,
    user=Depends(get_current_user),
    service: ExampleService = Depends(get_example_service),
):
    try:
        return await service.get_if_accessible(user, example_id)
    except Exception as e:
        _raise_http(e)

@router.post("", response_model=ExampleDTO, status_code=201)
async def create_example(
    body: ExampleCreateDTO,
    user=Depends(get_current_user),
    service: ExampleService = Depends(get_example_service),
):
    try:
        return await service.create(user, body)
    except Exception as e:
        _raise_http(e)
```

Controller returns **DTOs** (or list envelopes). It does not map ORM itself.

### Service (uses repository + mapper)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from lib.db.error import DBNotFoundError
from lib.pagination import ListOptions
from .dto import ExampleCreateDTO, ExampleDTO, ExampleListResponseDTO, ExampleUpdateDTO
from .error import ExampleNotAccessibleError, ExampleNotFoundError
from .mapper import ExampleMapper
from .repository import ExampleRepository

class ExampleService:
    def __init__(
        self,
        db: AsyncSession,
        repository: ExampleRepository,
        permission_checker: PermissionChecker,
    ):
        self.db = db
        self.repository = repository
        self.permission_checker = permission_checker
        self.mapper = ExampleMapper()

    async def list_for_project(
        self, user, project_id, list_options: ListOptions = ListOptions()
    ) -> ExampleListResponseDTO:
        if not await self.permission_checker.can_view_example(user.id, project_id):
            raise ExampleNotAccessibleError(f"Project {project_id} not accessible")
        page = await self.repository.list_by_project(
            project_id, list_options=list_options
        )
        return ExampleListResponseDTO.from_page(
            page.map(self.mapper.to_dto)
        )

    async def get_if_accessible(self, user, example_id) -> ExampleDTO:
        try:
            row = await self.repository.get_by_id(example_id)
        except DBNotFoundError as e:
            raise ExampleNotFoundError(str(e)) from e
        if not await self.permission_checker.can_view_example(user.id, row.project_id):
            raise ExampleNotAccessibleError(f"Example {example_id} not accessible")
        return self.mapper.to_dto(row)

    async def create(self, user, dto: ExampleCreateDTO) -> ExampleDTO:
        if not await self.permission_checker.can_edit_example(user.id, dto.project_id):
            raise ExampleNotAccessibleError(...)
        try:
            row = await self.repository.create(self.mapper.from_create_dto(dto))
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return self.mapper.to_dto(row)

    async def update(self, user, example_id, dto: ExampleUpdateDTO) -> ExampleDTO:
        # load + RBAC ...
        updates = self.mapper.to_update_dict(dto)  # exclude_unset, snake_case keys
        try:
            row = await self.repository.update(example_id, **updates)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return self.mapper.to_dto(row)
```

### Repository (Advanced Alchemy via BaseRepository)

```python
from lib.db.base_repository import BaseRepository
from lib.pagination import ListOptions, Page
from models import Example
from sqlalchemy.ext.asyncio import AsyncSession

class ExampleRepository(BaseRepository[Example]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Example)

    async def list_by_project(
        self,
        project_id,
        list_options: ListOptions | None = None,
    ) -> Page[Example]:
        return await self.list(
            Example.project_id == project_id,
            order_by=Example.created_at.desc(),
            list_options=list_options,  # triggers LimitOffset + list_and_count
        )
```

## Shared camelCase DTO config

```python
# lib/dto_config.py
from pydantic import ConfigDict, AliasGenerator
from pydantic.alias_generators import to_camel

def model_config() -> ConfigDict:
    return ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=to_camel,      # accept camelCase JSON in
            serialization_alias=to_camel,   # emit camelCase JSON out
        ),
        extra="forbid",
        populate_by_name=True,  # also accept snake_case when validating in-process
    )
```

Effects:

| Side | Convention |
|------|------------|
| Python / ORM / mappers | `project_id`, `created_at`, `display_name` |
| HTTP JSON + OpenAPI | `projectId`, `createdAt`, `displayName` |
| External clients | **Send camelCase** in bodies |
| Query params | Use camelCase names or `Query(..., alias="projectId")` |

FastAPI response models using these DTOs serialize with aliases (same as `model_dump(mode="json", by_alias=True)`).

### DTO examples

```python
from uuid import UUID
from pydantic import BaseModel, Field
from lib.dto_config import model_config
from lib.pagination import PaginatedResponse

class ExampleCreateDTO(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=512)
    description: str = Field(default="", max_length=512)
    model_config = model_config()

class ExampleUpdateDTO(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=512)
    description: str | None = Field(None, max_length=512)
    model_config = model_config()

class ExampleDTO(ExampleCreateDTO):
    id: UUID
    created_at: datetime  # use shared ApiDateTime if project emits Z
    updated_at: datetime
    model_config = model_config()

class ExampleListResponseDTO(PaginatedResponse[ExampleDTO]):
    """Wire: { data, hasNext, size, total }."""
```

Wire create body:

```json
{ "projectId": "...", "name": "x", "description": "" }
```

## Mapper

Keep ORM construction and DTO shaping out of controllers/services logic blobs:

```python
from typing import Any
from lib.dto_converter import DtoConverter
from models import Example
from .dto import ExampleCreateDTO, ExampleDTO, ExampleUpdateDTO

class ExampleMapper:
    def to_dto(self, row: Example) -> ExampleDTO:
        return ExampleDTO(
            id=row.id,
            project_id=row.project_id,
            name=row.name,
            description=row.description,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def from_create_dto(self, dto: ExampleCreateDTO) -> Example:
        return Example(
            project_id=dto.project_id,
            name=dto.name,
            description=dto.description,
        )

    def to_update_dict(self, dto: ExampleUpdateDTO) -> dict[str, Any]:
        # by_alias=False → snake_case keys for setattr / repository.update
        return DtoConverter(ExampleUpdateDTO).dto_to_partial_dict_with_dto_case(dto)
```

`DtoConverter` helpers:

| Method | Use |
|--------|-----|
| `dto_to_dict_with_dto_case` | Full dump, snake_case keys |
| `dto_to_partial_dict_with_dto_case` | `exclude_unset=True` for PATCH |
| `dto_to_json_dict_with_json_case` | camelCase dict (rare; prefer response_model) |
| `dict_with_json_case_to_dto` | `model_validate` camelCase or snake_case dict |

## Advanced Alchemy (`BaseRepository`)

Wrap `SQLAlchemyAsyncRepository` with **`auto_commit=False`** so services own transactions.

| Method | Behavior |
|--------|----------|
| `create` / `add` | `add(..., auto_refresh=True)` |
| `get_by_id` | `get_one`; map Alchemy `NotFoundError` → `DBNotFoundError` |
| `update` | load, setattr fields, `repository.update` |
| `list(*filters, order_by=, load=, list_options=)` | If `list_options`: append Alchemy `LimitOffset`, call `list_and_count`, build `Page`. If omitted: plain `list`, `total=len(rows)`, `has_next=False` |
| `delete` | Prefer Core `DELETE FROM … WHERE id = :id` (avoid ORM `session.delete` collisions with `lazy="raise"` graphs) |
| `expunge` | Detach loaded instance before Core delete when needed |
| `commit` / `rollback` | Delegate to session; call from **service** |

Pass eager loads via `load=` (e.g. `selectinload(...)`) because relationships use `lazy="raise"`.

Do **not** import `LimitOffset` in controllers/services — only `ListOptions`. The base repo converts:

```python
LimitOffset(offset=options.offset, limit=options.limit)
```

## Pagination end-to-end

### Types (`lib/pagination.py`)

```python
MAX_LIST_PAGE_SIZE = 100

class ListOptions(BaseModel):
    limit: int = Field(default=MAX_LIST_PAGE_SIZE, ge=1, le=MAX_LIST_PAGE_SIZE)
    offset: int = Field(default=0, ge=0)

@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    data: list[T]
    has_next: bool
    total: int
    def map(self, mapper: Callable[[T], U]) -> Page[U]: ...

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    has_next: bool = False
    size: int = 0
    total: int = 0
    model_config = model_config()  # → hasNext, etc.

    @classmethod
    def from_page(cls, page: Page[T]) -> PaginatedResponse[T]:
        return cls(data=page.data, has_next=page.has_next, size=page.size, total=page.total)
```

### Required flow for list endpoints

1. Controller: `limit`/`offset` Query (`ge`/`le`), build `ListOptions`.
2. Service: pass `list_options` into repository after RBAC.
3. Repository: `self.list(..., list_options=list_options)` → DB `LIMIT`/`OFFSET` + count.
4. Service: `page.map(mapper.to_dto)` then `PaginatedResponse.from_page(...)`.
5. Response JSON: `{ "data": [...], "hasNext": true, "size": 10, "total": 42 }`.

### Rules

- Prefer DB pagination (`list_options` on repository). Use `paginate_sequence` only for already-materialized lists.
- Cap `limit` at `MAX_LIST_PAGE_SIZE` in both Query and `ListOptions`.
- `has_next = offset + len(data) < total` (computed in `BaseRepository.list` when paginating).
- List response DTOs should subclass `PaginatedResponse[ItemDTO]` (or alias it) so OpenAPI stays consistent.
