"""Shared wiring for domain services against a live ClickHouse client."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.domain.artifacts_info.service import ArtifactsInfoService
from app.domain.last_logged.service import LastLoggedService
from app.domain.projects.service import ProjectsService
from app.domain.scalars.service import ScalarsService


async def wait_for_clickhouse(
    predicate,
    *,
    timeout: float = 5.0,
    interval: float = 0.1,
    err: str = "timeout waiting for ClickHouse",
) -> None:
    """Poll until ``await predicate()`` is true (mutations are asynchronous)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await predicate():
            return
        await asyncio.sleep(interval)
    raise AssertionError(err)


@dataclass
class DomainServices:
    """One shared ``LastLoggedService`` wired into scalars and artifacts (matches FastAPI DI)."""

    projects: ProjectsService
    scalars: ScalarsService
    artifacts: ArtifactsInfoService
    last_logged: LastLoggedService


def domain_services(client) -> DomainServices:
    last_logged = LastLoggedService(client)
    scalars = ScalarsService(client, cache=None, last_logged_service=last_logged)
    artifacts = ArtifactsInfoService(client, last_logged_service=last_logged)
    projects = ProjectsService(scalars, artifacts, last_logged)
    return DomainServices(
        projects=projects,
        scalars=scalars,
        artifacts=artifacts,
        last_logged=last_logged,
    )
