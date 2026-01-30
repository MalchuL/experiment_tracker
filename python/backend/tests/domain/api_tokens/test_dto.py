from datetime import datetime

import pytest
from pydantic import ValidationError

from domain.api_tokens.dto import (
    ApiTokenCreateDTO,
    ApiTokenCreateResponseDTO,
    ApiTokenListItemDTO,
    ApiTokenUpdateDTO,
)
from lib.dto_converter import DtoConverter


class TestApiTokenCreateDTO:
    INPUT_DATA = {
        "name": "Test token",
        "description": "Token description",
        "scopes": ["projects:read"],
        "expiresInDays": 30,
    }

    def test_create_dto_validation(self):
        converter = DtoConverter[ApiTokenCreateDTO](ApiTokenCreateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.description == self.INPUT_DATA["description"]
        assert dto.scopes == self.INPUT_DATA["scopes"]
        assert dto.expires_in_days == self.INPUT_DATA["expiresInDays"]

    def test_create_dto_serialization(self):
        converter = DtoConverter[ApiTokenCreateDTO](ApiTokenCreateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA

    def test_create_dto_extra_forbid(self):
        converter = DtoConverter[ApiTokenCreateDTO](ApiTokenCreateDTO)
        data = dict(self.INPUT_DATA)
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(data)


class TestApiTokenCreateResponseDTO:
    INPUT_DATA = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Created token",
        "token": "pat_created",
        "createdAt": "2021-01-01T00:00:00Z",
    }

    def test_create_response_dto_validation(self):
        converter = DtoConverter[ApiTokenCreateResponseDTO](ApiTokenCreateResponseDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.id) == self.INPUT_DATA["id"]
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.token == self.INPUT_DATA["token"]
        assert dto.created_at == datetime.fromisoformat(self.INPUT_DATA["createdAt"])

    def test_create_response_dto_serialization(self):
        converter = DtoConverter[ApiTokenCreateResponseDTO](ApiTokenCreateResponseDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA


class TestApiTokenListItemDTO:
    INPUT_DATA = {
        "id": "123e4567-e89b-12d3-a456-426614174111",
        "name": "List token",
        "description": "List description",
        "scopes": ["projects:read", "projects:write"],
        "createdAt": "2021-01-02T00:00:00Z",
        "expiresAt": "2021-02-02T00:00:00Z",
        "revoked": False,
        "lastUsedAt": "2021-01-03T00:00:00Z",
    }

    def test_list_item_dto_validation(self):
        converter = DtoConverter[ApiTokenListItemDTO](ApiTokenListItemDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.id) == self.INPUT_DATA["id"]
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.description == self.INPUT_DATA["description"]
        assert dto.scopes == self.INPUT_DATA["scopes"]
        assert dto.created_at == datetime.fromisoformat(self.INPUT_DATA["createdAt"])
        assert dto.expires_at == datetime.fromisoformat(self.INPUT_DATA["expiresAt"])
        assert dto.revoked is False
        assert dto.last_used_at == datetime.fromisoformat(self.INPUT_DATA["lastUsedAt"])

    def test_list_item_dto_serialization(self):
        converter = DtoConverter[ApiTokenListItemDTO](ApiTokenListItemDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA


class TestApiTokenUpdateDTO:
    INPUT_DATA = {
        "name": "Updated token",
        "description": "Updated description",
        "scopes": ["projects:write"],
        "expiresInDays": 90,
    }

    def test_update_dto_validation(self):
        converter = DtoConverter[ApiTokenUpdateDTO](ApiTokenUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.description == self.INPUT_DATA["description"]
        assert dto.scopes == self.INPUT_DATA["scopes"]
        assert dto.expires_in_days == self.INPUT_DATA["expiresInDays"]

    def test_update_dto_serialization(self):
        converter = DtoConverter[ApiTokenUpdateDTO](ApiTokenUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA
