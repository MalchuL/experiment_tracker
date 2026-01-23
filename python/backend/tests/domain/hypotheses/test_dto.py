from datetime import datetime

import pytest
from pydantic import ValidationError

from domain.hypotheses.dto import (
    HypothesisCreateDTO,
    HypothesisDTO,
    HypothesisUpdateDTO,
)
from lib.dto_converter import DtoConverter


class TestHypothesisDTO:
    INPUT_DATA = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "projectId": "223e4567-e89b-12d3-a456-426614174000",
        "title": "Hypothesis 1",
        "description": "Hypothesis description",
        "author": "Author",
        "status": "testing",
        "targetMetrics": ["accuracy"],
        "baseline": "root",
        "createdAt": "2021-01-01T00:00:00Z",
        "updatedAt": "2021-01-02T00:00:00Z",
    }

    def test_hypothesis_dto_validation(self):
        converter = DtoConverter[HypothesisDTO](HypothesisDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.id) == self.INPUT_DATA["id"]
        assert str(dto.project_id) == self.INPUT_DATA["projectId"]
        assert dto.title == self.INPUT_DATA["title"]
        assert dto.description == self.INPUT_DATA["description"]
        assert dto.author == self.INPUT_DATA["author"]
        assert dto.status == self.INPUT_DATA["status"]
        assert dto.target_metrics == self.INPUT_DATA["targetMetrics"]
        assert dto.baseline == self.INPUT_DATA["baseline"]
        assert dto.created_at == datetime.fromisoformat(self.INPUT_DATA["createdAt"])
        assert dto.updated_at == datetime.fromisoformat(self.INPUT_DATA["updatedAt"])

    def test_hypothesis_dto_serialization(self):
        converter = DtoConverter[HypothesisDTO](HypothesisDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA

    def test_hypothesis_dto_extra_forbid(self):
        converter = DtoConverter[HypothesisDTO](HypothesisDTO)
        data = dict(self.INPUT_DATA)
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(data)


class TestHypothesisCreateDTO:
    INPUT_DATA = {
        "projectId": "223e4567-e89b-12d3-a456-426614174000",
        "title": "Hypothesis Create",
        "description": "Create description",
        "author": "Author",
        "status": "proposed",
        "targetMetrics": ["accuracy"],
        "baseline": "root",
    }

    def test_hypothesis_create_dto_validation(self):
        converter = DtoConverter[HypothesisCreateDTO](HypothesisCreateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.project_id) == self.INPUT_DATA["projectId"]
        assert dto.title == self.INPUT_DATA["title"]
        assert dto.status == self.INPUT_DATA["status"]

    def test_hypothesis_create_dto_serialization(self):
        converter = DtoConverter[HypothesisCreateDTO](HypothesisCreateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped["projectId"] == self.INPUT_DATA["projectId"]
        assert dumped["title"] == self.INPUT_DATA["title"]

    def test_hypothesis_create_dto_extra_forbid(self):
        converter = DtoConverter[HypothesisCreateDTO](HypothesisCreateDTO)
        data = dict(self.INPUT_DATA)
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(data)


class TestHypothesisUpdateDTO:
    INPUT_DATA = {
        "title": "Hypothesis Updated",
        "description": "Updated description",
        "author": "Updated Author",
        "status": "supported",
        "targetMetrics": ["latency"],
        "baseline": "new-baseline",
    }

    def test_hypothesis_update_dto_validation(self):
        converter = DtoConverter[HypothesisUpdateDTO](HypothesisUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.title == self.INPUT_DATA["title"]
        assert dto.status == self.INPUT_DATA["status"]
        assert dto.target_metrics == self.INPUT_DATA["targetMetrics"]

    def test_hypothesis_update_dto_serialization(self):
        converter = DtoConverter[HypothesisUpdateDTO](HypothesisUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped["title"] == self.INPUT_DATA["title"]
        assert dumped["status"] == self.INPUT_DATA["status"]
        assert dumped["targetMetrics"] == self.INPUT_DATA["targetMetrics"]
