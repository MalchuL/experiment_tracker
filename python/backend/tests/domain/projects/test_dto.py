from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from domain.projects.dashboard.dto import DashboardStatsDTO
from domain.projects.dto import (
    ProjectCreateDTO,
    ProjectDTO,
    ProjectMetricDTO,
    ProjectMetricKeyDTO,
    ProjectSettingDTO,
    ProjectUpdateDTO,
)
from lib.dto_converter import DtoConverter


class TestProjectDTO:
    INPUT_DATA = {
        "name": "test_project",
        "description": "test_description",
        "owner": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "displayName": "Test User",
        },
        "team": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test Team",
        },
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "createdAt": "2021-01-01T00:00:00Z",
        "experimentCount": 12,
        "hypothesisCount": 13,
        "metrics": {
            "trackedMetrics": [
                {
                    "name": "test_metric",
                    "direction": "minimize",
                    "aggregation": "last",
                }
            ],
            "displayMetrics": ["test_metric"],
        },
        "settings": [
            {
                "name": "namingPattern",
                "description": "",
                "type": "string",
                "value": "{num}_from_{parent}_{change}",
            }
        ],
    }

    def test_project_dto_validation(self):
        converter = DtoConverter[ProjectDTO](ProjectDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.metrics.tracked_metrics[0].name == "test_metric"
        assert dto.metrics.display_metrics == [
            ProjectMetricKeyDTO(name="test_metric", label=None)
        ]
        assert dto.settings[0].name == "namingPattern"
        assert dto.settings[0].type == "string"
        assert dto.created_at == datetime.fromisoformat(self.INPUT_DATA["createdAt"])
        assert dto.id == UUID(self.INPUT_DATA["id"])

    def test_project_dto_serialization(self):
        converter = DtoConverter[ProjectDTO](ProjectDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped_data = converter.dto_to_json_dict_with_json_case(dto)
        assert dumped_data["metrics"]["trackedMetrics"][0]["name"] == "test_metric"
        assert dumped_data["metrics"]["displayMetrics"] == [
            {"name": "test_metric", "label": None}
        ]
        assert dumped_data["settings"][0]["name"] == "namingPattern"


class TestProjectSettingDTO:
    INPUT_DATA = {
        "name": "maxEpochs",
        "description": "",
        "type": "int",
        "value": 100,
    }

    def test_project_setting_dto_validation(self):
        converter = DtoConverter[ProjectSettingDTO](ProjectSettingDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == "maxEpochs"
        assert dto.type == "int"
        assert dto.value == 100

    def test_project_setting_extra_forbid(self):
        with pytest.raises(ValidationError):
            converter = DtoConverter[ProjectSettingDTO](ProjectSettingDTO)
            converter.dict_with_json_case_to_dto(
                {**self.INPUT_DATA, "extraField": "not-allowed"}
            )


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


class TestProjectUpdateDTO:
    INPUT_DATA = {
        "name": "test_project",
        "description": "test_description",
        "metrics": {
            "trackedMetrics": [
                {
                    "name": "test_metric",
                    "direction": "minimize",
                    "aggregation": "last",
                }
            ],
            "displayMetrics": ["test_metric"],
        },
        "settings": [
            {
                "name": "runConfig",
                "description": "",
                "type": "json",
                "value": {"seed": 42},
            }
        ],
    }

    def test_project_update_dto_validation(self):
        converter = DtoConverter[ProjectUpdateDTO](ProjectUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.metrics.tracked_metrics[0].name == "test_metric"
        assert dto.settings[0].name == "runConfig"

    def test_project_update_dto_serialization_with_snake_case(self):
        converter = DtoConverter[ProjectUpdateDTO](ProjectUpdateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        dumped_data = converter.dto_to_partial_dict_with_dto_case(dto)
        assert dumped_data["metrics"]["tracked_metrics"][0]["name"] == "test_metric"
        assert dumped_data["metrics"]["display_metrics"] == [
            {"name": "test_metric", "label": None}
        ]
        assert dumped_data["settings"][0]["type"] == "json"


class TestDashboardStatsDTO:
    INPUT_DATA = {
        "totalExperiments": 5,
        "runningExperiments": 2,
        "completedExperiments": 1,
        "failedExperiments": 2,
        "totalHypotheses": 3,
        "supportedHypotheses": 1,
        "refutedHypotheses": 2,
    }

    def test_dashboard_stats_dto_validation(self):
        converter = DtoConverter[DashboardStatsDTO](DashboardStatsDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.totalExperiments == self.INPUT_DATA["totalExperiments"]
        assert dto.runningExperiments == self.INPUT_DATA["runningExperiments"]


class TestProjectCreateDTO:
    INPUT_DATA = {
        "name": "test_project",
        "description": "test_description",
        "teamId": "123e4567-e89b-12d3-a456-426614174000",
        "metrics": {
            "trackedMetrics": [
                {
                    "name": "test_metric",
                    "direction": "minimize",
                    "aggregation": "last",
                }
            ],
            "displayMetrics": ["test_metric"],
        },
        "settings": [
            {
                "name": "namingPattern",
                "description": "",
                "type": "string",
                "value": "{num}_from_{parent}_{change}",
            }
        ],
    }

    def test_project_create_dto_validation(self):
        converter = DtoConverter[ProjectCreateDTO](ProjectCreateDTO)
        dto = converter.dict_with_json_case_to_dto(self.INPUT_DATA)
        assert dto.name == self.INPUT_DATA["name"]
        assert dto.metrics.tracked_metrics[0].name == "test_metric"
        assert dto.settings[0].name == "namingPattern"
        assert dto.team_id == UUID(self.INPUT_DATA["teamId"])
