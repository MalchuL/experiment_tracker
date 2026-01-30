from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.api_tokens.repository import ApiTokenRepository
from models import ApiToken, User


async def _create_token(
    db_session: AsyncSession,
    user: User,
    *,
    name: str,
    token_hash: str,
    created_at: datetime | None = None,
    scopes: list[str] | None = None,
) -> ApiToken:
    token = ApiToken(
        user_id=user.id,
        token_hash=token_hash,
        name=name,
        description="Repo token",
        scopes=scopes or ["projects:read"],
        created_at=created_at,
    )
    db_session.add(token)
    await db_session.flush()
    await db_session.refresh(token)
    return token


class TestApiTokenRepository:
    @pytest.fixture
    def api_token_repository(self, db_session: AsyncSession) -> ApiTokenRepository:
        return ApiTokenRepository(db_session)

    async def test_get_by_id_filters_by_user(
        self,
        api_token_repository: ApiTokenRepository,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ) -> None:
        token = await _create_token(
            db_session,
            test_user,
            name="User token",
            token_hash="hash_user",
        )

        result = await api_token_repository.get_by_id(token.id, test_user_2.id)

        assert result is None

    async def test_list_by_user_orders_desc(
        self,
        api_token_repository: ApiTokenRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        await _create_token(
            db_session,
            test_user,
            name="Older",
            token_hash="hash_old",
            created_at=datetime(2024, 1, 1),
        )
        await _create_token(
            db_session,
            test_user,
            name="Newer",
            token_hash="hash_new",
            created_at=datetime(2024, 1, 2),
        )

        tokens = await api_token_repository.list_by_user(test_user.id)
        names = [token.name for token in tokens]

        assert names == ["Newer", "Older"]

    async def test_get_by_hash_returns_token(
        self,
        api_token_repository: ApiTokenRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        token = await _create_token(
            db_session,
            test_user,
            name="Hash token",
            token_hash="hash_lookup",
        )

        result = await api_token_repository.get_by_hash("hash_lookup")

        assert result is not None
        assert result.id == token.id

    async def test_update_persists_changes(
        self,
        api_token_repository: ApiTokenRepository,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        token = await _create_token(
            db_session,
            test_user,
            name="Original",
            token_hash="hash_update",
        )
        token.name = "Updated"
        token.revoked = True

        updated = await api_token_repository.update(token)

        assert updated.name == "Updated"
        assert updated.revoked is True
