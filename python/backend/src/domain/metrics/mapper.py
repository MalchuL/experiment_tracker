from typing import Any, Dict, Iterable, List

from lib.dto_converter import DtoConverter
from models import Metric as MetricModel

from .dto import MetricDTO
from .dto import MetricCreateDTO, MetricUpdateDTO


class MetricMapper:
    def metric_schema_to_dto(self, metric: MetricModel) -> MetricDTO:
        return MetricDTO.model_validate(metric, from_attributes=True)

    def metric_list_schema_to_dto(
        self, metrics: Iterable[MetricModel]
    ) -> List[MetricDTO]:
        return [self.metric_schema_to_dto(metric) for metric in metrics]

    def metric_create_dto_to_schema(self, data: MetricCreateDTO) -> MetricModel:
        return MetricModel(
            experiment_id=data.experiment_id,
            name=data.name,
            value=data.value,
            step=data.step,
            label=data.label,
        )

    def metric_update_dto_to_update_dict(self, data: MetricUpdateDTO) -> Dict[str, Any]:
        converter = DtoConverter[MetricUpdateDTO](MetricUpdateDTO)
        converted_dto = converter.dto_to_partial_dict_with_dto_case(data)
        updates: Dict[str, Any] = {}
        if "name" in converted_dto:
            updates["name"] = converted_dto["name"]
        if "value" in converted_dto:
            updates["value"] = converted_dto["value"]
        if "step" in converted_dto:
            updates["step"] = converted_dto["step"]
        if "label" in converted_dto:
            updates["label"] = converted_dto["label"]
        return updates
