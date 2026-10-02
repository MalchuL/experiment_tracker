---
name: frontend-architecture
description: Organize a Next.js frontend with DDD domain folders, axios services, TanStack Query hooks, Zustand client state, App Router route groups, runtime-editable API base URLs (not NEXT_PUBLIC build-time), and a standalone Docker web image. Use when adding or changing UI features, pages, components, API clients, auth, env config, or the frontend container.
---

# Frontend architecture

Apply this layout and layering for Next.js App Router frontends. Do not invent parallel layers (extra “repositories”, global Redux, or baking deploy-specific API URLs into `NEXT_PUBLIC_*` at build time).

## Layout (where files live)

```
apps/web/                      # or equivalent frontend package root
├── Dockerfile                 # standalone Next image (build from monorepo root)
├── .env.example               # documented local env
├── next.config.ts             # output: "standalone"
└── src/
    ├── app/                   # App Router (pages + BFF Route Handlers)
    ├── components/
    │   ├── ui/                # design-system primitives only
    │   └── shared/            # cross-domain UI (shell, page header, tables…)
    ├── domain/                # bounded contexts (DDD)
    ├── lib/                   # app-wide infra (api clients, env, constants, utils)
    ├── types/                 # shared frontend-only types
    └── styles/                # shared style helpers when needed
```

Path alias: `@/*` → `src/*`.

## DDD: `src/domain/<context>/`

One folder per bounded context (e.g. `auth`, `users`, `teams`, feature areas of the product).

Typical slices (create only what you need):

| Slice | Role |
|-------|------|
| `types/` | Domain models and DTOs used by UI + services |
| `schemas/` | Zod forms / validation (`satisfies z.ZodType<…>`) |
| `services/` | Axios HTTP calls to the backend (or BFF) |
| `hooks/` | TanStack Query wrappers + domain providers |
| `store/` | Zustand for **client** UI/session state only |
| `components/` | Domain-specific React UI |
| `utils/` / `lib/` | Pure helpers for that domain |
| `index.ts` | Re-exports for clean imports |

Nested subdomains are OK when a parent context grows large (`domain/<parent>/<child>/`).

**Rules**

- Pages under `app/` stay thin: compose domain hooks + domain/shared components.
- Domain A may import types/services from domain B sparingly; prefer hooks/services over reaching into another domain’s components.
- Do not put backend proxy logic in domain services — use `app/api/**` Route Handlers when the browser must go through Next (cookies, binary streams).

## Components

| Location | Use for |
|----------|---------|
| `components/ui/*` | Design-system primitives (Button, Dialog…). Avoid business logic. |
| `components/shared/*` | Reused across domains (app shell, page header, generic upload). |
| `domain/<ctx>/components/*` | Feature UI tied to that context (tables, charts, settings forms). |

Prefer `"use client"` only where hooks/state/browser APIs are required. Keep server Components for layouts that only wrap children when possible.

## Routes (`src/app`)

Use **route groups** for layout, not URL segments:

| Group / path | Purpose |
|--------------|---------|
| `(auth)/…` | Unauthenticated pages (login, register) |
| `(core)/…` | Logged-in app chrome |
| `(core)/(workspace)/…` | Shared workspace shell (lists, docs, top-level nav) |
| `(core)/<resource>/[id]/…` | Resource-scoped feature pages |
| `admin/` (optional) | Ops UI with a **separate** auth channel (not end-user JWT) |
| `api/**` | BFF Route Handlers → backend with `getServerApiBaseUrl()` |

### `FRONTEND_ROUTES` vs `API_ROUTES`

Centralize in `src/lib/constants/`:

| Constant | Use for |
|----------|---------|
| `FRONTEND_ROUTES` | In-app navigation / `href` builders / guard public-path checks |
| `API_ROUTES` | Backend paths for axios (never mix into `Link`/`router.push`) |
| `QUERY_KEYS` | TanStack Query cache keys |

Keep `isPublicFrontendPath(pathname)` next to `FRONTEND_ROUTES` for the auth guard (login/register/admin bootstrap, etc.).

Add new page routes under the matching group. Prefer `page.tsx` that imports from `domain/*`; colocate page-only hooks under the route folder only when they are truly page-specific.

### Resource-scoped domain Provider

For nested routes under `[resourceId]`, wrap children in a domain Provider in that segment’s `layout.tsx`. Descendants read via `useCurrentX()` instead of prop-drilling the loaded resource.

Root layout injects runtime config and wraps app providers (`QueryClientProvider`, theme, auth). Keep `export const dynamic = "force-dynamic"` on the root layout so runtime env is not statically frozen.

## Auth

### Cookie token utils + auth headers

- `domain/auth/utils/token.ts`: SSR-safe `getAuthToken` / `setAuthToken` / `deleteAuthToken` (guard with `typeof document === "undefined"`).
- `domain/auth/utils/headers.ts`: `getAuthHeaders()` → `{ Authorization: Bearer … }` when a token exists.
- Cookie name is a single constant (e.g. `auth_token`); path `/`.

### Zustand session + Query user bootstrap

- Zustand store holds `token`, `user`, `isAuthenticated`, `isLoading`.
- Hydrate `token` / `isAuthenticated` from the cookie at store create-time (sync).
- Load current user with TanStack Query keyed by token (e.g. `["auth", token]`), `enabled` only when token exists and user is missing; on 401 clear token.
- Split concerns: cookie = “logged in?”, Query = “who am I?”.

Wire `AuthProvider` (facade over the domain auth hook) + `AuthGuard` (redirect using `isPublicFrontendPath`) in app providers.

### Separate ops/admin auth channel

Ops/admin UI may use a different credential (e.g. admin key in `sessionStorage`, sent as `X-Admin-Key`) and must not share the end-user JWT cookie flow. Mark those paths public for the JWT guard; protect them inside the admin UI itself.

## Services (axios)

1. Implement an interface + object in `domain/<ctx>/services/<name>-service.ts`.
2. Call a shared client from `@/lib/api/clients/axios-client` (e.g. `serviceClients.api`).
3. Use `API_ROUTES.*` path constants; type responses with domain types.
4. **Normalize at the service boundary** before returning (flatten nested API DTOs into stable UI models) so Query caches the domain shape, not the wire shape.
5. Re-export from `services/index.ts`.

```ts
export const exampleService = {
  getById: async (id: string) => {
    const { data } = await serviceClients.api.get(API_ROUTES.EXAMPLE.BY_ID(id));
    return normalizeExample(data);
  },
};
```

### Axios interceptors + `ErrorResponse`

Shared client (`@/lib/api/clients/axios-client`):

- `baseURL` from `getPublicApiBaseUrl()`.
- Request interceptor: merge `getAuthHeaders()`.
- Response interceptor: on 401 clear token / Authorization; map API `detail` into `ErrorResponse`.
- UI uses `getErrorMessage(error, fallback)` from `@/lib/api/error-response` for toasts/copy — do not parse `error.response` in components.

**BFF / Route Handlers** (`app/api/**`): use `fetch` + `getServerApiBaseUrl()` from `@/lib/env` (Compose DNS like `http://backend:8000`), forward cookies/Authorization. Do not point browser axios at internal Docker hostnames.

## TanStack Query

### Shared QueryClient factory

- `createQueryClient()` in `@/lib/api/clients/query-client` owns default `staleTime`, `gcTime`, `retry`, `retryDelay`, `refetchOnWindowFocus` (often production-only), `refetchOnReconnect`.
- Instantiate once in client providers: `useState(() => createQueryClient())`.

### Domain hooks

- Call services inside `useQuery` / `useInfiniteQuery` / `useMutation`.
- Always use `QUERY_KEYS` for `queryKey`; invalidate the same prefix after mutations.
- Expose a stable hook API (`isLoading`, mutations, refetch) rather than leaking raw query objects everywhere.

### Infinite query modes (`auto` vs `scroll`)

Support both modes from one infinite hook when a domain needs it:

| Mode | Behavior |
|------|----------|
| `auto` | `useEffect` keeps `fetchNextPage` until `hasNext` is false (full dataset for charts/aggregations) |
| `scroll` | IntersectionObserver / “load more” for large tables |

`getNextPageParam` should use cumulative offset + `hasNext` from the shared pagination contract.

### Named refresh-rate constants

Put poll intervals in `@/lib/constants/` (e.g. `rates.ts`, `live-refresh.ts`) and pass them as `refetchInterval`. Do not hardcode magic ms values in hooks/components.

## Zustand

Use Zustand for **client-only** state: auth session UI, view preferences, canvas layout — not as a cache for server lists.

- Server/async data → TanStack Query + services.
- Ephemeral UI / persisted local preferences → Zustand.

### `persist` + stable empty selectors

When using `zustand/middleware` `persist`:

- Export module-level empty fallbacks (`EMPTY_POSITIONS = {}`) and return those from selectors for missing keys.
- Do **not** return inline `{}` / `[]` from selectors — that breaks `useSyncExternalStore` snapshot caching (React 19).

## Schemas (Zod)

Align form schemas with domain types and backend limits:

```ts
export const insertExampleSchema = z.object({
  name: z.string().min(1).max(ENTITY_NAME_MAX_LEN),
  description: z.string().max(ENTITY_DESCRIPTION_MAX_LEN).default(""),
}) satisfies z.ZodType<InsertExample>;
```

- Keep shared max lengths in `@/lib/validation/` (match API validation).
- Prefer `satisfies z.ZodType<DomainType>` so schemas cannot drift from TypeScript models.
- Drive `react-hook-form` via `zodResolver` inside **domain** dialogs/forms, not in thin pages.

## URL selection codec

For multi-select (or id lists) in the query string:

- Encode as base64(JSON string array); omit the param when empty / “all selected” if that shortens URLs.
- Keep a `decodeLegacy…` path for older bookmark formats so shared links keep working.
- Prefer pure utils under the domain (`utils/selection-codec.ts`); page hooks own when to read/write the URL.

## Environment variables (editable at runtime)

**Do not** put deploy-specific API base URLs in `NEXT_PUBLIC_*` if operators must change them without rebuilding. Those values are inlined at `next build`.

| Variable | Where read | Purpose |
|----------|------------|---------|
| `PUBLIC_API_BASE_URL` | Server at request time → injected for browser | Browser-reachable backend origin |
| `SERVER_API_BASE_URL` | Server only (`env.ts`) | BFF → API (e.g. `http://backend:8000`) |
| `NEXT_PUBLIC_API_PREFIX` | Optional build-time public non-secret | Path prefix hints (default `/api`) |

Mechanism:

1. `@/lib/runtime-config` — `getPublicApiBaseUrl()`, `getRuntimeConfigScript()`.
2. Root `app/layout.tsx` embeds the script into a browser global (e.g. `window.__APP_RUNTIME_CONFIG__`).
3. `@/lib/env` — Zod-validated server env; `getServerApiBaseUrl()`.

### Env Zod validation (actionable boot errors)

Validate once at module load. On `ZodError`, throw a message that lists **missing** vs **invalid** variables and points at `.env` / Compose env — fail fast, not a vague parse error mid-request.

Document locals in `.env.example`. Never put secrets into runtime config exposed to the browser.

Details and Compose wiring: [runtime-and-docker.md](runtime-and-docker.md).

## Adding a feature (checklist)

```
- [ ] Domain folder under src/domain/<context>/ (types → service → hooks → components)
- [ ] API_ROUTES + QUERY_KEYS (+ FRONTEND_ROUTES if new page)
- [ ] Normalize wire DTOs in the service before caching
- [ ] Thin page under the correct app/ route group; resource Provider in [id]/layout when needed
- [ ] Shared/ui only if truly cross-cutting or primitive
- [ ] BFF route only if browser cannot call the API directly (auth cookie proxy, streaming files)
- [ ] Zod schema satisfies domain type; use shared entity limits
- [ ] User-facing errors via getErrorMessage; refresh intervals via named constants
- [ ] No new NEXT_PUBLIC_* for URLs that must change per deployment
```

## Anti-patterns

- Business components dumped into `components/ui`
- Fetching with raw `axios.create` outside the shared service client
- Caching server entities only in Zustand
- Hardcoding `/api/...` or UI paths instead of `API_ROUTES` / `FRONTEND_ROUTES`
- Mixing frontend hrefs and backend paths in one constants bag
- Returning inline `{}` from Zustand selectors (use stable empty constants)
- Using `NEXT_PUBLIC_*` for API base URLs so images need rebuild on URL change
- Pointing browser clients at Docker-internal hosts (`backend:8000`)
- Parsing axios `error.response` in UI instead of `ErrorResponse` / `getErrorMessage`
- Reusing end-user JWT cookie flow for a separate ops/admin credential
