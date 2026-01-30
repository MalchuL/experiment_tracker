from typing import List

from models import ApiToken

from .dto import ApiTokenCreateResponseDTO, ApiTokenListItemDTO


class ApiTokenMapper:
    def token_schema_to_list_item_dto(self, token: ApiToken) -> ApiTokenListItemDTO:
        return ApiTokenListItemDTO(
            id=token.id,
            name=token.name,
            description=token.description,
            scopes=token.scopes or [],
            created_at=token.created_at,
            expires_at=token.expires_at,
            revoked=token.revoked,
            last_used_at=token.last_used_at,
        )

    def token_schema_list_to_list_item_dto(
        self, tokens: List[ApiToken]
    ) -> List[ApiTokenListItemDTO]:
        return [self.token_schema_to_list_item_dto(token) for token in tokens]

    def token_schema_to_create_response_dto(
        self, token: ApiToken, raw_token: str
    ) -> ApiTokenCreateResponseDTO:
        return ApiTokenCreateResponseDTO(
            id=token.id,
            name=token.name,
            token=raw_token,
            created_at=token.created_at,
        )
