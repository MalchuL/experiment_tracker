# File descriptors & local services

When you run the **scalars service**, **backend**, or **object storage** locally (for example via `run_local_stack.sh` at the repo root), you may hit **`Too many open files`** or confusing **`Device or resource busy`** errors from ClickHouse clients. This page explains what is going on and where to look in the codebase.

:::note
This is a **developer runbook**. End users on a hosted deployment rarely need to think about per-process FD limits; operators tune limits on servers.
:::

## What a file descriptor (FD) is

An **FD** is a small integer the operating system uses for an open resource: files, **TCP sockets** (listening port, each accepted client, each outbound connection to ClickHouse or another HTTP service), pipes, and more. Each process has a **soft limit** on how many FDs it may open (`RLIMIT_NOFILE`; often **1024** in local shells). Exceeding it produces **`OSError: [Errno 24] Too many open files`**, including on **`socket.accept()`** inside asyncio/uvicorn.

**FD usage is not the same as RAM (RSS).** You can approach the FD limit without a dramatic “memory leak” graph: many sockets use kernel bookkeeping that does not look like heap growth.

## Typical symptom order (e.g. scalars on port 8001)

1. **`[Errno 24] Too many open files`** on **`accept()`** — the service cannot accept new inbound HTTP connections.
2. Soon after, **`httpx`** or **`clickhouse_connect`** may log **`[Errno 16] Device or resource busy`** on **`getaddrinfo`** / **`connect`** when opening **new** sockets. That is usually a **follow-on** from FD exhaustion, not “ClickHouse is overloaded” by itself.

Restarting the process clears FDs. If the open count **creeps up again** under modest traffic, investigate leaks or very high concurrent connection counts.

## How to inspect FD usage (Linux)

Use the **worker** PID — the process that actually holds your HTTP port (for scalars, often **8001**), not necessarily the uvicorn reload parent.

- **Count open FDs:** `ls /proc/PID/fd | wc -l`
- **Soft/hard limits:** `grep Max /proc/PID/limits` (see **Max open files**).
- **What they are:** `lsof -p PID -nP` (many `TCP`/`IPv4` rows usually means connection load).

`ulimit -n` in your **current shell** may differ from the limit **inherited by the server** you started from a terminal or IDE; **`/proc/PID/limits`** is authoritative for a running process.

## `run_local_stack_prod.sh` and `uvicorn --reload`

The repo root script **`run_local_stack_prod.sh`** starts the Python services with **`uvicorn` without `--reload`** (production-like processes) and runs the web app via **`pnpm run build`** then **`pnpm run start`**. That avoids the reload parent/worker split for local stack runs.

If you start services manually with **`uvicorn ... --reload`** (see **`LOCAL_RUN.md`**), reload mode uses a **parent** process plus a **spawned worker child** that runs the FastAPI app. You may see a process command line containing **`multiprocessing.spawn`** / **`spawn_main`** — that is **expected** for the reload worker, not extra logic added by this product’s app code.

**Reload does not stack old workers’ FDs on one process:** when files change, the **old child exits** and a **new child** starts with a **fresh** FD table. If FD counts **rise over time without** constantly saving files, treat that as **request load / connection patterns** (or a leak), not as “reload keeps opening FDs forever.”

## Repo paths that affect connection churn

**Backend — new `httpx.AsyncClient` per outbound call** (high churn under parallel load; each call still closes via `async with`, but concurrency opens many sockets at once):

- `python/backend/src/clients/scalars/client.py` — `_request`
- `python/backend/src/clients/artifacts_info/client.py`
- `python/backend/src/clients/object_storage/client.py` (multiple call sites)

**Scalars — ClickHouse client:** `python/scalars_service/src/db/clickhouse.py` keeps a **single shared async client** per process (`init_clickhouse_client` / `close_clickhouse_client` in app lifespan), wired via `python/scalars_service/src/api/service_dependencies.py`. Concurrent requests reuse that client instead of opening a new TCP connection per request.

## Mitigations

- Raise **`LimitNOFILE`** / **`ulimit -n`** for local development.
- Prefer a **single shared `httpx.AsyncClient`** (or a small pool) per backend process for satellite HTTP instead of constructing a client on every `_request`.
- Run **`uvicorn` without `--reload`** when you need to stress-test or measure stable FD behavior.

For architecture and stack layout, see [Architecture overview](/docs/architecture-overview). Repository-wide agent runbook (including a pointer here): **`AGENTS.md`** at the repo root.
