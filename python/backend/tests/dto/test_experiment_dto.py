from datetime import datetime
import pytest
from pydantic import ValidationError

from domain.experiments.dto import (
    ExperimentCreateDTO,
    ExperimentDTO,
    ExperimentParseResultDTO,
    ExperimentReorderDTO,
    ExperimentUpdateDTO,
)
from lib.dto_converter import DtoConverter


class TestExperimentDTO:
    INPUT_DATA = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "projectId": "223e4567-e89b-12d3-a456-426614174000",
        "name": "exp_1",
        "description": "experiment description",
        "status": "planned",
        "parentExperimentId": None,
        "features": {"seed": 42},
        "featuresDiff": {"seed": 1},
        "gitDiff": "diff --git a b",
        "progress": 10,
        "color": "#123456",
        "order": 2,
        "createdAt": "2021-01-01T00:00:00Z",
        "startedAt": "2021-01-02T00:00:00Z",
        "completedAt": None,
    }

    def test_experiment_dto_validation(self):
        converter = DtoConverter[ExperimentDTO](ExperimentDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.id) == self.INPUT_DATA["id"]
        assert str(dto.project_id) == self.INPUT_DATA["projectId"]
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.description == self.INPUT_DATA["description"]
        assert dto.status == self.INPUT_DATA["status"]
        assert dto.parent_experiment_id is None
        assert dto.features == self.INPUT_DATA["features"]
        assert dto.features_diff == self.INPUT_DATA["featuresDiff"]
        assert dto.git_diff == self.INPUT_DATA["gitDiff"]
        assert dto.progress == self.INPUT_DATA["progress"]
        assert dto.color == self.INPUT_DATA["color"]
        assert dto.order == self.INPUT_DATA["order"]
        assert dto.created_at == datetime.fromisoformat(self.INPUT_DATA["createdAt"])
        assert dto.started_at == datetime.fromisoformat(self.INPUT_DATA["startedAt"])
        assert dto.completed_at == self.INPUT_DATA["completedAt"] == None

    def test_experiment_dto_serialization(self):
        converter = DtoConverter[ExperimentDTO](ExperimentDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA

    def test_experiment_dto_extra_forbid(self):
        converter = DtoConverter[ExperimentDTO](ExperimentDTO)
        data = dict(self.INPUT_DATA)
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(data)


class TestExperimentCreateDTO:
    INPUT_DATA = {
        "projectId": "223e4567-e89b-12d3-a456-426614174000",
        "name": "exp_1",
        "description": "experiment description",
        "status": "planned",
        "parentExperimentId": None,
        "features": {"seed": 42},
        "gitDiff": None,
        "color": "#123456",
        "order": 1,
        "parentExperimentName": "0_from_root_baseline",
    }

    def test_experiment_create_dto_validation(self):
        converter = DtoConverter[ExperimentCreateDTO](ExperimentCreateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.project_id) == self.INPUT_DATA["projectId"]
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.parent_experiment_name == self.INPUT_DATA["parentExperimentName"]

    def test_experiment_create_dto_serialization(self):
        converter = DtoConverter[ExperimentCreateDTO](ExperimentCreateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped["projectId"] == self.INPUT_DATA["projectId"]
        assert dumped["parentExperimentName"] == self.INPUT_DATA["parentExperimentName"]

    def test_experiment_create_dto_extra_forbid(self):
        converter = DtoConverter[ExperimentCreateDTO](ExperimentCreateDTO)
        data = dict(self.INPUT_DATA)
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(data)


class TestExperimentUpdateDTO:
    INPUT_DATA = {
        "name": "exp_2",
        "description": "updated",
        "status": "running",
        "progress": 50,
        "order": 3,
    }

    def test_experiment_update_dto_validation(self):
        converter = DtoConverter[ExperimentUpdateDTO](ExperimentUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.status == self.INPUT_DATA["status"]
        assert dto.progress == self.INPUT_DATA["progress"]
        assert dto.order == self.INPUT_DATA["order"]

    def test_experiment_update_dto_serialization(self):
        converter = DtoConverter[ExperimentUpdateDTO](ExperimentUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped["name"] == self.INPUT_DATA["name"]
        assert dumped["status"] == self.INPUT_DATA["status"]
        assert dumped["progress"] == self.INPUT_DATA["progress"]
        assert dumped["order"] == self.INPUT_DATA["order"]


class TestExperimentParseResultDTO:
    INPUT_DATA = {"num": "1", "parent": "root", "change": "seed"}

    def test_parse_result_validation(self):
        converter = DtoConverter[ExperimentParseResultDTO](ExperimentParseResultDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.num == self.INPUT_DATA["num"]
        assert dto.parent == self.INPUT_DATA["parent"]
        assert dto.change == self.INPUT_DATA["change"]

    def test_parse_result_serialization(self):
        converter = DtoConverter[ExperimentParseResultDTO](ExperimentParseResultDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA


class TestExperimentReorderDTO:
    INPUT_DATA = {
        "experimentIds": [
            "123e4567-e89b-12d3-a456-426614174000",
            "223e4567-e89b-12d3-a456-426614174000",
        ]
    }

    def test_reorder_dto_validation(self):
        converter = DtoConverter[ExperimentReorderDTO](ExperimentReorderDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert [str(value) for value in dto.experiment_ids] == self.INPUT_DATA[
            "experimentIds"
        ]

    def test_reorder_dto_serialization(self):
        converter = DtoConverter[ExperimentReorderDTO](ExperimentReorderDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA
