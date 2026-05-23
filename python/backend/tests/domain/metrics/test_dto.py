from datetime import datetime

import pytest
from pydantic import ValidationError

from domain.metrics.dto import MetricDTO, MetricUpsertDTO
from lib.dto_converter import DtoConverter


class TestMetricDTO:
    INPUT_DATA = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "experimentId": "223e4567-e89b-12d3-a456-426614174000",
        "name": "accuracy",
        "value": 0.95,
        "label": "train",
        "createdAt": "2021-01-01T00:00:00Z",
    }

    def test_metric_dto_validation(self):
        converter = DtoConverter[MetricDTO](MetricDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.id) == self.INPUT_DATA["id"]
        assert str(dto.experiment_id) == self.INPUT_DATA["experimentId"]
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.value == self.INPUT_DATA["value"]
        assert dto.label == self.INPUT_DATA["label"]
        assert dto.created_at == datetime.fromisoformat(self.INPUT_DATA["createdAt"])

    def test_metric_dto_serialization(self):
        converter = DtoConverter[MetricDTO](MetricDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA

    def test_metric_dto_extra_forbid(self):
        converter = DtoConverter[MetricDTO](MetricDTO)
        data = dict(self.INPUT_DATA)
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(data)


class TestMetricUpsertDTO:
    INPUT_DATA = {
        "experimentId": "223e4567-e89b-12d3-a456-426614174000",
        "name": "loss",
        "value": 1.23,
        "label": None,
    }

    def test_metric_upsert_dto_validation(self):
        converter = DtoConverter[MetricUpsertDTO](MetricUpsertDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert str(dto.experiment_id) == self.INPUT_DATA["experimentId"]
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.value == self.INPUT_DATA["value"]
        assert dto.label is self.INPUT_DATA.get("label")

    def test_metric_upsert_dto_serialization(self):
        converter = DtoConverter[MetricUpsertDTO](MetricUpsertDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped == self.INPUT_DATA

    def test_metric_upsert_dto_extra_forbid(self):
        converter = DtoConverter[MetricUpsertDTO](MetricUpsertDTO)
        data = dict(self.INPUT_DATA)
        data["extra"] = "nope"
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(data)

    def test_metric_upsert_empty_label_string_becomes_none(self):
        """API may send label: '' for unlabeled; store/query as NULL like None."""
        data = {
            "experimentId": "223e4567-e89b-12d3-a456-426614174000",
            "name": "loss",
            "value": 1.23,
            "label": "",
        }
        converter = DtoConverter[MetricUpsertDTO](MetricUpsertDTO)
        dto = converter.dict_with_json_case_to_dto(data)
        assert dto.label is None

    def test_metric_upsert_name_max_length_boundary(self):
        converter = DtoConverter[MetricUpsertDTO](MetricUpsertDTO)
        ok = {
            "experimentId": "223e4567-e89b-12d3-a456-426614174000",
            "name": "x" * 512,
            "value": 1.0,
            "label": None,
        }
        dto = converter.dict_with_json_case_to_dto(ok)
        assert len(dto.name) == 512

        bad = {**ok, "name": "y" * 513}
        with pytest.raises(ValidationError):
            converter.dict_with_json_case_to_dto(bad)
