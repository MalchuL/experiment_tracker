from typing import Any, Dict, List

from lib.dto_converter import DtoConverter
from .dto import (
    HypothesisCreateDTO,
    HypothesisDTO,
    HypothesisUpdateDTO,
)
from models import Hypothesis


class HypothesisMapper:
    def __init__(self):
        pass

    def hypothesis_schema_to_dto(self, hypothesis: Hypothesis) -> HypothesisDTO:
        return HypothesisDTO(
            id=hypothesis.id,
            project_id=hypothesis.project_id,
            title=hypothesis.title,
            description=hypothesis.description,
            author=hypothesis.author,
            status=hypothesis.status,
            target_metrics=hypothesis.target_metrics,
            baseline=hypothesis.baseline,
            created_at=hypothesis.created_at,
            updated_at=hypothesis.updated_at,
        )

    def hypothesis_list_schema_to_dto(
        self, hypotheses: List[Hypothesis]
    ) -> List[HypothesisDTO]:
        return [self.hypothesis_schema_to_dto(hypothesis) for hypothesis in hypotheses]

    def hypothesis_create_dto_to_schema(
        self, hypothesis: HypothesisCreateDTO
    ) -> Hypothesis:
        return Hypothesis(
            project_id=hypothesis.project_id,
            title=hypothesis.title,
            description=hypothesis.description,
            author=hypothesis.author,
            status=hypothesis.status,
            target_metrics=hypothesis.target_metrics,
            baseline=hypothesis.baseline,
        )

    def hypothesis_update_dto_to_update_dict(
        self, hypothesis: HypothesisUpdateDTO
    ) -> Dict[str, Any]:
        converter = DtoConverter[HypothesisUpdateDTO](HypothesisUpdateDTO)
        converted_dto = converter.dto_to_partial_dict_with_dto_case(hypothesis)
        updates: Dict[str, Any] = {}
        if "title" in converted_dto:
            updates["title"] = converted_dto["title"]
        if "description" in converted_dto:
            updates["description"] = converted_dto["description"]
        if "author" in converted_dto:
            updates["author"] = converted_dto["author"]
        if "status" in converted_dto:
            updates["status"] = converted_dto["status"]
        if "target_metrics" in converted_dto:
            updates["target_metrics"] = converted_dto["target_metrics"]
        if "baseline" in converted_dto:
            updates["baseline"] = converted_dto["baseline"]
        return updates
