from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.api_tokens.error import (
    ApiTokenExpiredError,
    ApiTokenInvalidError,
    ApiTokenRevokedError,
)
from domain.api_tokens.service import (
    ApiTokenService,
    TOKEN_CACHE,
    hash_token,
)
from models import User, utc_now


@pytest.fixture(autouse=True)
def clear_token_cache() -> None:
    TOKEN_CACHE._cache.clear()
    yield
    TOKEN_CACHE._cache.clear()


class TestApiTokenService:
    @pytest.fixture
    def api_token_service(self, db_session: AsyncSession) -> ApiTokenService:
        return ApiTokenService(db_session)

    async def test_create_token_returns_dto(
        self, api_token_service: ApiTokenService, test_user: User
    ) -> None:
        dto = await api_token_service.create_token(
            user_id=test_user.id,
            name="Service token",
            description="Service description",
            scopes=["projects:read"],
            expires_in_days=30,
        )

        assert dto.id is not None
        assert dto.name == "Service token"
        assert dto.token.startswith("pat_")
        assert dto.created_at is not None

        stored = await api_token_service.repo.get_by_id(dto.id, test_user.id)
        assert stored is not None
        assert stored.token_hash == hash_token(dto.token)

    async def test_list_tokens_returns_list_items(
        self, api_token_service: ApiTokenService, test_user: User
    ) -> None:
        await api_token_service.create_token(
            user_id=test_user.id,
            name="First",
            description=None,
            scopes=["projects:read"],
            expires_in_days=None,
        )
        await api_token_service.create_token(
            user_id=test_user.id,
            name="Second",
            description=None,
            scopes=["projects:write"],
            expires_in_days=None,
        )

        tokens = await api_token_service.list_tokens(test_user.id)
        names = [token.name for token in tokens]

        assert names == ["Second", "First"]

    async def test_update_token_updates_fields(
        self, api_token_service: ApiTokenService, test_user: User
    ) -> None:
        created = await api_token_service.create_token(
            user_id=test_user.id,
            name="Original",
            description="Original description",
            scopes=["projects:read"],
            expires_in_days=None,
        )

        updated = await api_token_service.update_token(
            user_id=test_user.id,
            token_id=created.id,
            name="Updated",
            description="Updated description",
            scopes=["projects:write"],
            expires_in_days=10,
        )

        assert updated.name == "Updated"
        assert updated.description == "Updated description"
        assert updated.scopes == ["projects:write"]
        assert updated.expires_at is not None

    async def test_revoke_token_marks_revoked(
        self, api_token_service: ApiTokenService, test_user: User
    ) -> None:
        created = await api_token_service.create_token(
            user_id=test_user.id,
            name="Revocable",
            description=None,
            scopes=["projects:read"],
            expires_in_days=None,
        )

        revoked = await api_token_service.revoke_token(test_user.id, created.id)

        assert revoked.revoked is True

    async def test_validate_token_raises_for_invalid(self, api_token_service) -> None:
        with pytest.raises(ApiTokenInvalidError):
            await api_token_service.validate_token("pat_invalid")

    async def test_validate_token_raises_for_revoked(
        self, api_token_service: ApiTokenService, test_user: User
    ) -> None:
        created = await api_token_service.create_token(
            user_id=test_user.id,
            name="Revoked",
            description=None,
            scopes=["projects:read"],
            expires_in_days=None,
        )
        token = await api_token_service.repo.get_by_id(created.id, test_user.id)
        assert token is not None
        token.revoked = True
        await api_token_service.repo.update(token)

        with pytest.raises(ApiTokenRevokedError):
            await api_token_service.validate_token(created.token)

    async def test_validate_token_raises_for_expired(
        self, api_token_service: ApiTokenService, test_user: User
    ) -> None:
        created = await api_token_service.create_token(
            user_id=test_user.id,
            name="Expired",
            description=None,
            scopes=["projects:read"],
            expires_in_days=None,
        )
        token = await api_token_service.repo.get_by_id(created.id, test_user.id)
        assert token is not None
        token.expires_at = utc_now() - timedelta(days=1)
        await api_token_service.repo.update(token)

        with pytest.raises(ApiTokenExpiredError):
            await api_token_service.validate_token(created.token)

    async def test_get_user_for_token_updates_last_used(
        self, api_token_service: ApiTokenService, test_user: User
    ) -> None:
        created = await api_token_service.create_token(
            user_id=test_user.id,
            name="Usage",
            description=None,
            scopes=["projects:read"],
            expires_in_days=None,
        )

        user = await api_token_service.get_user_for_token(created.token)
        assert user.id == test_user.id

        token = await api_token_service.repo.get_by_id(created.id, test_user.id)
        assert token is not None
        assert token.last_used_at is not None
