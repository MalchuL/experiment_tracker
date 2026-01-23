from datetime import datetime

import pytest
from pydantic import ValidationError

from domain.metrics.dto import Metric, MetricCreate, MetricUpdate
from lib.dto_converter import DtoConverter


class TestMetricDTO:
    INPUT_DATA = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "experimentId": "223e4567-e89b-12d3-a456-426614174000",
        "name": "accuracy",
        "value": 0.95,
        "step": 3,
        "direction": "maximize",
        "createdAt": "2021-01-01T00:00:00Z",
    }

    def test_metric_dto_validation(self):
        converter = DtoConverter[Metric](Metric)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.id) == self.INPUT_DATA["id"]
        assert str(dto.experiment_id) == self.INPUT_DATA["experimentId"]
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.value == self.INPUT_DATA["value"]
        assert dto.step == self.INPUT_DATA["step"]
        assert dto.direction == self.INPUT_DATA["direction"]
        assert dto.created_at == datetime.fromisoformat(self.INPUT_DATA["createdAt"])

    def test_metric_dto_serialization(self):
        converter = DtoConverter[Metric](Metric)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA

    def test_metric_dto_extra_forbid(self):
        converter = DtoConverter[Metric](Metric)
        data = dict(self.INPUT_DATA)
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(data)


class TestMetricCreateDTO:
    INPUT_DATA = {
        "experimentId": "223e4567-e89b-12d3-a456-426614174000",
        "name": "loss",
        "value": 1.23,
        "step": 0,
        "direction": "minimize",
    }

    def test_metric_create_dto_validation(self):
        converter = DtoConverter[MetricCreate](MetricCreate)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.experiment_id) == self.INPUT_DATA["experimentId"]
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.value == self.INPUT_DATA["value"]
        assert dto.step == self.INPUT_DATA["step"]
        assert dto.direction == self.INPUT_DATA["direction"]

    def test_metric_create_dto_serialization(self):
        converter = DtoConverter[MetricCreate](MetricCreate)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA

    def test_metric_create_dto_extra_forbid(self):
        converter = DtoConverter[MetricCreate](MetricCreate)
        data = dict(self.INPUT_DATA)
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(data)


class TestMetricUpdateDTO:
    INPUT_DATA = {
        "name": "updated-loss",
        "value": 0.9,
        "step": 2,
        "direction": "maximize",
    }

    def test_metric_update_dto_validation(self):
        converter = DtoConverter[MetricUpdate](MetricUpdate)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.value == self.INPUT_DATA["value"]
        assert dto.step == self.INPUT_DATA["step"]
        assert dto.direction == self.INPUT_DATA["direction"]

    def test_metric_update_dto_serialization(self):
        converter = DtoConverter[MetricUpdate](MetricUpdate)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA
