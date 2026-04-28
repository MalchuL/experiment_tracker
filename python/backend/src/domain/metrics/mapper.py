from typing import Iterable, List

from models import Metric as MetricModel

from .dto import MetricDTO, MetricUpsertDTO


class MetricMapper:
    def metric_schema_to_dto(self, metric: MetricModel) -> MetricDTO:
        return MetricDTO.model_validate(metric, from_attributes=True)

    def metric_list_schema_to_dto(
        self, metrics: Iterable[MetricModel]
    ) -> List[MetricDTO]:
        return [self.metric_schema_to_dto(metric) for metric in metrics]

    def metric_upsert_dto_to_schema(self, data: MetricUpsertDTO) -> MetricModel:
        return MetricModel(
            experiment_id=data.experiment_id,
            name=data.name,
            value=data.value,
            label=data.label,
        )
