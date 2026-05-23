from __future__ import annotations

from typing import cast

from ...request_types import ApiRequestSpec
from .dto import HealthCheckResponse


class HealthRequestSpecFactory:
    ENDPOINTS = {
        "healthcheck": "/",
    }

    def get_healthcheck(self) -> ApiRequestSpec[HealthCheckResponse]:
        endpoint = cast(str, self.ENDPOINTS["healthcheck"])
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=HealthCheckResponse,
        )


HealthService = HealthRequestSpecFactory
