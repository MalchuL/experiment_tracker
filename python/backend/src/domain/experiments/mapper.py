from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from lib.dto_converter import DtoConverter
from lib.types import UUID_TYPE
from .dto import (
    ExperimentCreateDTO,
    ExperimentDTO,
    ExperimentParseResultDTO,
    ExperimentUpdateDTO,
)
from .utils import ExperimentParseResult
from models import Experiment


@dataclass
class CreateDTOToSchemaProps:
    """Props for converting ExperimentCreateDTO to Experiment schema"""

    owner_id: UUID_TYPE
    parent_experiment_id: Optional[UUID_TYPE]


class ExperimentMapper:
    def __init__(self):
        pass

    def experiment_parse_result_to_dto(
        self, result: ExperimentParseResult
    ) -> ExperimentParseResultDTO:
        return ExperimentParseResultDTO(
            num=result.num,
            parent=result.parent,
            change=result.change,
        )

    def experiment_schema_to_dto(self, experiment: Experiment) -> ExperimentDTO:
        return ExperimentDTO(
            id=experiment.id,
            project_id=experiment.project_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status,
            parent_experiment_id=experiment.parent_experiment_id,
            features=experiment.features,
            features_diff=experiment.features_diff,
            git_diff=experiment.git_diff,
            progress=experiment.progress,
            color=experiment.color,
            order=experiment.order,
            created_at=experiment.created_at,
            started_at=experiment.started_at,
            completed_at=experiment.completed_at,
        )

    def experiment_list_schema_to_dto(
        self, experiments: List[Experiment]
    ) -> List[ExperimentDTO]:
        return [self.experiment_schema_to_dto(experiment) for experiment in experiments]

    def experiment_create_dto_to_schema(
        self, experiment: ExperimentDTO, props: CreateDTOToSchemaProps
    ) -> Experiment:
        return Experiment(
            project_id=experiment.project_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status,
            parent_experiment_id=experiment.parent_experiment_id
            or props.parent_experiment_id,
            features=experiment.features,
            git_diff=experiment.git_diff,
            color=experiment.color,
            order=experiment.order,
        )

    def experiment_update_dto_to_update_dict(
        self, experiment: ExperimentUpdateDTO
    ) -> Dict[str, Any]:
        converter = DtoConverter[ExperimentUpdateDTO](ExperimentUpdateDTO)
        converted_dto = converter.dto_to_partial_dict_with_dto_case(experiment)
        updates = {}
        if "name" in converted_dto:
            updates["name"] = converted_dto["name"]
        if "description" in converted_dto:
            updates["description"] = converted_dto["description"]
        if "parent_experiment_id" in converted_dto:
            updates["parent_experiment_id"] = converted_dto["parent_experiment_id"]
        if "color" in converted_dto:
            updates["color"] = converted_dto["color"]
        if "status" in converted_dto:
            updates["status"] = converted_dto["status"]
        if "features" in converted_dto:
            updates["features"] = converted_dto["features"]
        if "git_diff" in converted_dto:
            updates["git_diff"] = converted_dto["git_diff"]
        if "progress" in converted_dto:
            updates["progress"] = converted_dto["progress"]
        if "order" in converted_dto:
            updates["order"] = converted_dto["order"]
        return updates
