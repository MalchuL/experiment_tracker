from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from domain.api_tokens.mapper import ApiTokenMapper
from models import ApiToken, User


async def _create_token(
    db_session: AsyncSession,
    user: User,
    *,
    name: str = "Token",
    token_hash: str = "hash_1",
    description: str | None = "Token description",
    scopes: list[str] | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    revoked: bool = False,
    last_used_at: datetime | None = None,
) -> ApiToken:
    token = ApiToken(
        user_id=user.id,
        token_hash=token_hash,
        name=name,
        description=description,
        scopes=scopes or ["projects:read"],
        created_at=created_at,
        expires_at=expires_at,
        revoked=revoked,
        last_used_at=last_used_at,
    )
    db_session.add(token)
    await db_session.flush()
    await db_session.refresh(token)
    return token


class TestApiTokenMapper:
    async def test_token_schema_to_list_item_dto(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        mapper = ApiTokenMapper()
        created_at = datetime(2024, 1, 1)
        expires_at = datetime(2024, 2, 1)
        last_used_at = datetime(2024, 1, 3)
        token = await _create_token(
            db_session,
            test_user,
            name="API Token",
            token_hash="hash_abc",
            description="Mapper token",
            scopes=["projects:read", "projects:write"],
            created_at=created_at,
            expires_at=expires_at,
            revoked=True,
            last_used_at=last_used_at,
        )

        dto = mapper.token_schema_to_list_item_dto(token)

        assert dto.id == token.id
        assert dto.name == "API Token"
        assert dto.description == "Mapper token"
        assert dto.scopes == ["projects:read", "projects:write"]
        assert dto.created_at == created_at
        assert dto.expires_at == expires_at
        assert dto.revoked is True
        assert dto.last_used_at == last_used_at

    async def test_token_schema_list_to_list_item_dto(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        mapper = ApiTokenMapper()
        token = await _create_token(
            db_session,
            test_user,
            name="List Token",
            token_hash="hash_list",
        )

        dtos = mapper.token_schema_list_to_list_item_dto([token])

        assert len(dtos) == 1
        assert dtos[0].id == token.id
        assert dtos[0].name == "List Token"

    async def test_token_schema_to_create_response_dto(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        mapper = ApiTokenMapper()
        token = await _create_token(
            db_session,
            test_user,
            name="Create Token",
            token_hash="hash_create",
        )

        dto = mapper.token_schema_to_create_response_dto(token, "pat_raw_token")

        assert dto.id == token.id
        assert dto.name == "Create Token"
        assert dto.token == "pat_raw_token"
        assert dto.created_at == token.created_at
