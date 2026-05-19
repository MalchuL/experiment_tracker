from typing import Any, Dict, List

from lib.dto_converter import DtoConverter
from .dto import (
    ExperimentCreateDTO,
    ExperimentDTO,
    ExperimentListItemDTO,
    ExperimentUpdateDTO,
    FeatureNodeDTO,
)
from models import Experiment


def _feature_nodes_to_json(features: Any) -> List[Dict[str, Any]]:
    if not isinstance(features, list):
        return []
    result: List[Dict[str, Any]] = []
    for feature in features:
        if isinstance(feature, FeatureNodeDTO):
            result.append(feature.model_dump(exclude_none=True))
        elif isinstance(feature, dict):
            result.append(feature)
    return result


class ExperimentMapper:
    def __init__(self):
        pass

    def experiment_schema_to_dto(self, experiment: Experiment) -> ExperimentDTO:
        return ExperimentDTO(
            id=experiment.id,
            project_id=experiment.project_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status,
            parent_experiment_id=experiment.parent_experiment_id,
            features=experiment.features,
            progress=experiment.progress,
            color=experiment.color,
            order=experiment.order,
            tags=experiment.tags,
            created_at=experiment.created_at,
            started_at=experiment.started_at,
            completed_at=experiment.completed_at,
        )

    def experiment_schema_to_list_item_dto(
        self, experiment: Experiment, *, include_features: bool = True
    ) -> ExperimentListItemDTO:
        return ExperimentListItemDTO(
            id=experiment.id,
            project_id=experiment.project_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status,
            parent_experiment_id=experiment.parent_experiment_id,
            features=experiment.features if include_features else None,
            progress=experiment.progress,
            color=experiment.color,
            order=experiment.order,
            tags=experiment.tags,
            created_at=experiment.created_at,
            started_at=experiment.started_at,
            completed_at=experiment.completed_at,
        )

    def experiment_list_schema_to_dto(
        self, experiments: List[Experiment]
    ) -> List[ExperimentDTO]:
        return [self.experiment_schema_to_dto(experiment) for experiment in experiments]

    def experiment_create_dto_to_schema(
        self, experiment: ExperimentCreateDTO
    ) -> Experiment:
        return Experiment(
            project_id=experiment.project_id,
            name=experiment.name,
            description=experiment.description,
            status=experiment.status,
            parent_experiment_id=experiment.parent_experiment_id,
            features=_feature_nodes_to_json(experiment.features),
            color=experiment.color,
            order=experiment.order,
            tags=experiment.tags,
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
            updates["features"] = _feature_nodes_to_json(converted_dto["features"])
        if "progress" in converted_dto:
            updates["progress"] = converted_dto["progress"]
        if "order" in converted_dto:
            updates["order"] = converted_dto["order"]
        if "tags" in converted_dto:
            updates["tags"] = converted_dto["tags"]
        return updates
