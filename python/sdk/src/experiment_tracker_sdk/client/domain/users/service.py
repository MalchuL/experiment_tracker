from __future__ import annotations

from typing import cast

from ...request_types import ApiRequestSpec
from .dto import UserResponse


class UserRequestSpecFactory:
    ENDPOINTS = {
        "get_my_profile": "/users/me/profile",
    }

    def get_my_profile(self) -> ApiRequestSpec[UserResponse]:
        endpoint = cast(str, self.ENDPOINTS["get_my_profile"])
        return ApiRequestSpec(
            method="GET",
            endpoint=endpoint,
            response_model=UserResponse,
        )


UserService = UserRequestSpecFactory
