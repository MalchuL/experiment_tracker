# from datetime import datetime
# from uuid import UUID

# import pytest
# from pydantic import ValidationError

# from domain.experiments.dto import (
#     ExperimentCreateDTO,
#     ExperimentDTO,
#     ExperimentParseResultDTO,
#     ExperimentReorderDTO,
#     ExperimentUpdateDTO,
# )
# from lib.dto_converter import DtoConverter
# from models import ExperimentStatus


# class TestExperimentDTO:
#     INPUT_DATA = {
#         "projectId": "123e4567-e89b-12d3-a456-426614174000",
#         "name": "Experiment 1",
#         "description": "Experiment description",
#         "status": "planned",
#         "parentExperimentId": None,
#         "features": {"learningRate": 0.1},
#         "gitDiff": "diff",
#         "color": "#123456",
#         "order": 2,
#         "id": "123e4567-e89b-12d3-a456-426614174111",
#         "featuresDiff": {"learningRate": 0.05},
#         "progress": 10,
#         "createdAt": "2021-01-01T00:00:00Z",
#         "startedAt": "2021-01-02T00:00:00Z",
#         "completedAt": None,
#     }

#     def test_experiment_dto_validation(self):
#         converter = DtoConverter[ExperimentDTO](ExperimentDTO)
#         dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
#         assert str(dto.project_id) == self.INPUT_DATA["projectId"]
#         assert dto.name == self.INPUT_DATA["name"]
#         assert dto.description == self.INPUT_DATA["description"]
#         assert dto.status == ExperimentStatus.PLANNED
#         assert dto.features == self.INPUT_DATA["features"]
#         assert dto.git_diff == self.INPUT_DATA["gitDiff"]
#         assert dto.color == self.INPUT_DATA["color"]
#         assert dto.order == self.INPUT_DATA["order"]
#         assert str(dto.id) == self.INPUT_DATA["id"]
#         assert dto.features_diff == self.INPUT_DATA["featuresDiff"]
#         assert dto.progress == self.INPUT_DATA["progress"]
#         assert dto.created_at == datetime.fromisoformat(self.INPUT_DATA["createdAt"])
#         assert dto.started_at == datetime.fromisoformat(self.INPUT_DATA["startedAt"])
#         assert dto.completed_at is None

#     def test_experiment_dto_serialization(self):
#         converter = DtoConverter[ExperimentDTO](ExperimentDTO)
#         dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
#         dumped = converter.dto_to_json_dict_with_json_case(dto)
#         assert dumped["projectId"] == self.INPUT_DATA["projectId"]
#         assert dumped["name"] == self.INPUT_DATA["name"]
#         assert dumped["description"] == self.INPUT_DATA["description"]
#         assert dumped["status"] == self.INPUT_DATA["status"]
#         assert dumped["features"] == self.INPUT_DATA["features"]
#         assert dumped["gitDiff"] == self.INPUT_DATA["gitDiff"]
#         assert dumped["color"] == self.INPUT_DATA["color"]
#         assert dumped["order"] == self.INPUT_DATA["order"]
#         assert dumped["id"] == self.INPUT_DATA["id"]
#         assert dumped["featuresDiff"] == self.INPUT_DATA["featuresDiff"]
#         assert dumped["progress"] == self.INPUT_DATA["progress"]
#         assert dumped["createdAt"] == self.INPUT_DATA["createdAt"]


# class TestExperimentCreateDTO:
#     INPUT_DATA = {
#         "projectId": "123e4567-e89b-12d3-a456-426614174000",
#         "name": "Experiment Create",
#         "description": "Create description",
#         "status": "running",
#         "parentExperimentId": None,
#         "features": {"learningRate": 0.2},
#         "gitDiff": None,
#         "color": "#abcdef",
#         "order": 1,
#         "parentExperimentName": "1_from_root_seed",
#     }

#     def test_experiment_create_dto_validation(self):
#         converter = DtoConverter[ExperimentCreateDTO](ExperimentCreateDTO)
#         dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
#         assert str(dto.project_id) == self.INPUT_DATA["projectId"]
#         assert dto.name == self.INPUT_DATA["name"]
#         assert dto.status == ExperimentStatus.RUNNING
#         assert dto.parent_experiment_name == self.INPUT_DATA["parentExperimentName"]


# class TestExperimentUpdateDTO:
#     INPUT_DATA = {
#         "name": "Updated",
#         "description": "Updated description",
#         "status": "complete",
#         "features": {"learningRate": 0.3},
#         "gitDiff": "diff",
#         "progress": 50,
#         "order": 3,
#     }

#     def test_experiment_update_dto_partial_dict(self):
#         converter = DtoConverter[ExperimentUpdateDTO](ExperimentUpdateDTO)
#         dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
#         dumped = converter.dto_to_partial_dict_with_dto_case(dto)
#         assert dumped["name"] == self.INPUT_DATA["name"]
#         assert dumped["description"] == self.INPUT_DATA["description"]
#         assert dumped["status"] == ExperimentStatus.COMPLETE
#         assert dumped["features"] == self.INPUT_DATA["features"]
#         assert dumped["git_diff"] == self.INPUT_DATA["gitDiff"]
#         assert dumped["progress"] == self.INPUT_DATA["progress"]
#         assert dumped["order"] == self.INPUT_DATA["order"]


# class TestExperimentParseResultDTO:
#     def test_parse_result_dto_validation(self):
#         converter = DtoConverter[ExperimentParseResultDTO](ExperimentParseResultDTO)
#         dto = converter.dict_with_json_case_to_dto(
#             {"num": "1", "parent": "root", "change": "seed"}
#         )
#         assert dto.num == "1"
#         assert dto.parent == "root"
#         assert dto.change == "seed"


# class TestExperimentReorderDTO:
#     def test_reorder_dto_validation(self):
#         converter = DtoConverter[ExperimentReorderDTO](ExperimentReorderDTO)
#         dto = converter.dict_with_json_case_to_dto(
#             {"experimentIds": ["123e4567-e89b-12d3-a456-426614174000"]}
#         )
#         assert dto.experiment_ids == [UUID("123e4567-e89b-12d3-a456-426614174000")]

#     def test_reorder_dto_requires_list(self):
#         with pytest.raises(ValidationError):
#             ExperimentReorderDTO(experiment_ids="not-a-list")
