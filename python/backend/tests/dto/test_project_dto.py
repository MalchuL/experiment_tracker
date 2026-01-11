from datetime import datetime
from domain.projects.dto import (
    ProjectCreateDTO,
    ProjectDTO,
    ProjectMetricDTO,
    ProjectSettingsDTO,
    ProjectUpdateDTO,
)
from uuid import UUID
import pytest
from pydantic import ValidationError

from lib.dto_converter import DtoConverter


class TestProjectDTO:

    INPUT_DATA = {
        "name": "test_project",
        "description": "test_description",
        "owner": "test_owner",
        "ownerId": "123e4567-e89b-12d3-a456-426614174000",
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "createdAt": "2021-01-01T00:00:00Z",
        "experimentCount": 12,
        "hypothesisCount": 13,
        "metrics": [
            {
                "name": "test_metric",
                "direction": "minimize",
                "aggregation": "last",
            }
        ],
        "settings": {
            "namingPattern": "test_pattern",
            "displayMetrics": ["test_metric"],
        },
    }

    def test_project_dto_validation(self):
        converter = DtoConverter[ProjectDTO](ProjectDTO)

        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.description == self.INPUT_DATA["description"]
        assert dto.owner == self.INPUT_DATA["owner"]
        assert dto.metrics[0].name == self.INPUT_DATA["metrics"][0]["name"]
        assert dto.metrics[0].direction == self.INPUT_DATA["metrics"][0]["direction"]
        assert (
            dto.metrics[0].aggregation == self.INPUT_DATA["metrics"][0]["aggregation"]
        )
        assert (
            dto.settings.naming_pattern == self.INPUT_DATA["settings"]["namingPattern"]
        )
        assert (
            dto.settings.display_metrics
            == self.INPUT_DATA["settings"]["displayMetrics"]
        )
        assert dto.created_at == datetime.fromisoformat(self.INPUT_DATA["createdAt"])
        assert dto.experiment_count == self.INPUT_DATA["experimentCount"]
        assert dto.hypothesis_count == self.INPUT_DATA["hypothesisCount"]
        assert dto.id == UUID(self.INPUT_DATA["id"])

    def test_project_dto_serialization(self):
        converter = DtoConverter[ProjectDTO](ProjectDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped_data = dto.model_dump(by_alias=True, mode="json")
        assert dumped_data["name"] == self.INPUT_DATA["name"]
        assert dumped_data["description"] == self.INPUT_DATA["description"]
        assert dumped_data["owner"] == self.INPUT_DATA["owner"]
        assert dumped_data["metrics"] == self.INPUT_DATA["metrics"]
        assert dumped_data["settings"] == self.INPUT_DATA["settings"]
        assert dumped_data["createdAt"] == self.INPUT_DATA["createdAt"]
        assert dumped_data["experimentCount"] == self.INPUT_DATA["experimentCount"]
        assert dumped_data["hypothesisCount"] == self.INPUT_DATA["hypothesisCount"]
        assert dumped_data["id"] == self.INPUT_DATA["id"]

    def test_project_dto_deserialization(self):
        dumped_data = self.INPUT_DATA
        converter = DtoConverter[ProjectDTO](ProjectDTO)
        dto = converter.dict_with_json_case_to_dto(dumped_data)
        assert dto.name == dumped_data["name"]
        assert dto.description == dumped_data["description"]
        assert dto.owner == dumped_data["owner"]
        assert dto.metrics[0].name == dumped_data["metrics"][0]["name"]
        assert dto.metrics[0].direction == dumped_data["metrics"][0]["direction"]
        assert dto.metrics[0].aggregation == dumped_data["metrics"][0]["aggregation"]
        assert dto.settings.naming_pattern == dumped_data["settings"]["namingPattern"]
        assert dto.settings.display_metrics == dumped_data["settings"]["displayMetrics"]
        assert dto.created_at == datetime.fromisoformat(dumped_data["createdAt"])
        assert dto.experiment_count == dumped_data["experimentCount"]
        assert dto.hypothesis_count == dumped_data["hypothesisCount"]
        assert dto.id == UUID(dumped_data["id"])


class TestProjectSettingsDTO:

    INPUT_DATA = {
        "namingPattern": "test_pattern",
        "displayMetrics": ["test_metric"],
    }

    def test_project_settings_dto_validation(self):
        converter = DtoConverter[ProjectSettingsDTO](ProjectSettingsDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.naming_pattern == self.INPUT_DATA["namingPattern"]
        assert dto.display_metrics == self.INPUT_DATA["displayMetrics"]

    def test_project_settings_dto_serialization(self):
        converter = DtoConverter[ProjectSettingsDTO](ProjectSettingsDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        print(dto)
        dumped_data = converter.dto_to_json_dict_with_json_case(dto)
        print(dumped_data)
        assert dumped_data["namingPattern"] == self.INPUT_DATA["namingPattern"]
        assert dumped_data["displayMetrics"] == self.INPUT_DATA["displayMetrics"]

    def test_project_settings_dto_deserialization(self):
        dumped_data = self.INPUT_DATA
        converter = DtoConverter[ProjectSettingsDTO](ProjectSettingsDTO)
        dto = converter.dict_with_json_case_to_dto(dumped_data)
        assert dto.naming_pattern == dumped_data["namingPattern"]
        assert dto.display_metrics == dumped_data["displayMetrics"]

    def test_project_settings_extra_forbid(self):
        dumped_data = self.INPUT_DATA
        dumped_data["extra"] = "extra"
        with pytest.raises(ValidationError):
            converter = DtoConverter[ProjectSettingsDTO](ProjectSettingsDTO)
            converter.dict_with_json_case_to_dto(dumped_data)


class TestProjectMetricDTO:
    INPUT_DATA = {
        "name": "test_metric",
        "direction": "minimize",
        "aggregation": "last",
    }

    def test_project_metric_dto_validation(self):
        converter = DtoConverter[ProjectMetricDTO](ProjectMetricDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.direction == self.INPUT_DATA["direction"]
        assert dto.aggregation == self.INPUT_DATA["aggregation"]

    def test_project_metric_dto_serialization(self):
        converter = DtoConverter[ProjectMetricDTO](ProjectMetricDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped_data = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped_data["name"] == self.INPUT_DATA["name"]
        assert dumped_data["direction"] == self.INPUT_DATA["direction"]
        assert dumped_data["aggregation"] == self.INPUT_DATA["aggregation"]

    def test_project_metric_dto_deserialization(self):
        dumped_data = self.INPUT_DATA
        converter = DtoConverter[ProjectMetricDTO](ProjectMetricDTO)
        dto = converter.dict_with_json_case_to_dto(dumped_data)
        assert dto.name == dumped_data["name"]
        assert dto.direction == dumped_data["direction"]
        assert dto.aggregation == dumped_data["aggregation"]


class TestProjectUpdateDTO:
    INPUT_DATA = {
        "name": "test_project",
        "description": "test_description",
        # "owner": "test_owner",
        "metrics": [
            {
                "name": "test_metric",
                "direction": "minimize",
                "aggregation": "last",
            }
        ],
        "settings": {
            "namingPattern": "test_pattern",
            "displayMetrics": ["test_metric"],
        },
    }

    def test_project_update_dto_validation(self):
        converter = DtoConverter[ProjectUpdateDTO](ProjectUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.description == self.INPUT_DATA["description"]
        assert dto.owner == None
        assert dto.metrics[0].name == self.INPUT_DATA["metrics"][0]["name"]
        assert dto.metrics[0].direction == self.INPUT_DATA["metrics"][0]["direction"]
        assert (
            dto.metrics[0].aggregation == self.INPUT_DATA["metrics"][0]["aggregation"]
        )
        assert (
            dto.settings.naming_pattern == self.INPUT_DATA["settings"]["namingPattern"]
        )
        assert (
            dto.settings.display_metrics
            == self.INPUT_DATA["settings"]["displayMetrics"]
        )

    def test_project_update_dto_serialization_with_snake_case(self):
        converter = DtoConverter[ProjectUpdateDTO](ProjectUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped_data = converter.dto_to_partial_dict_with_dto_case(dto)
        assert dumped_data["name"] == self.INPUT_DATA["name"]
        assert dumped_data["description"] == self.INPUT_DATA["description"]
        assert "owner" not in dumped_data
        # Nested schemas should be in snake_case
        assert (
            dumped_data["metrics"][0]["name"] == self.INPUT_DATA["metrics"][0]["name"]
        )
        assert (
            dumped_data["metrics"][0]["direction"]
            == self.INPUT_DATA["metrics"][0]["direction"]
        )
        assert (
            dumped_data["metrics"][0]["aggregation"]
            == self.INPUT_DATA["metrics"][0]["aggregation"]
        )
        assert (
            dumped_data["settings"]["naming_pattern"]
            == self.INPUT_DATA["settings"]["namingPattern"]
        )
        assert (
            dumped_data["settings"]["display_metrics"]
            == self.INPUT_DATA["settings"]["displayMetrics"]
        )
        assert "created_at" not in dumped_data
        assert "id" not in dumped_data


class TestProjectCreateDTO:
    INPUT_DATA = {
        "name": "test_project",
        "description": "test_description",
        "owner": "test_owner",
        "teamId": "123e4567-e89b-12d3-a456-426614174000",
        "metrics": [
            {
                "name": "test_metric",
                "direction": "minimize",
                "aggregation": "last",
            }
        ],
        "settings": {
            "namingPattern": "test_pattern",
            "displayMetrics": ["test_metric"],
        },
    }

    def test_project_create_dto_validation(self):
        converter = DtoConverter[ProjectCreateDTO](ProjectCreateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.description == self.INPUT_DATA["description"]
        assert dto.metrics[0].name == self.INPUT_DATA["metrics"][0]["name"]
        assert (
            dto.settings.naming_pattern == self.INPUT_DATA["settings"]["namingPattern"]
        )
        assert (
            dto.settings.display_metrics
            == self.INPUT_DATA["settings"]["displayMetrics"]
        )
        assert dto.team_id == UUID(self.INPUT_DATA["teamId"])

    def test_project_create_dto_serialization(self):
        converter = DtoConverter[ProjectCreateDTO](ProjectCreateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped_data = converter.dto_to_dict_with_dto_case(dto)
        # Top-level fields should be in snake_case
        assert dumped_data["name"] == self.INPUT_DATA["name"]
        assert dumped_data["description"] == self.INPUT_DATA["description"]
        # Nested schemas should be in snake_case
        assert (
            dumped_data["metrics"][0]["name"] == self.INPUT_DATA["metrics"][0]["name"]
        )
        assert (
            dumped_data["metrics"][0]["direction"]
            == self.INPUT_DATA["metrics"][0]["direction"]
        )
        assert (
            dumped_data["metrics"][0]["aggregation"]
            == self.INPUT_DATA["metrics"][0]["aggregation"]
        )
        assert (
            dumped_data["settings"]["naming_pattern"]
            == self.INPUT_DATA["settings"]["namingPattern"]
        )
        assert (
            dumped_data["settings"]["display_metrics"]
            == self.INPUT_DATA["settings"]["displayMetrics"]
        )
        assert dumped_data["team_id"] == self.INPUT_DATA["teamId"]
