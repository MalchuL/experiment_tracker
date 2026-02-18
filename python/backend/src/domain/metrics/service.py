from typing import Dict, Iterable, List

from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from lib.db.base_repository import DBNotFoundError
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from models import MetricAggregation, MetricDirection
from sqlalchemy.ext.asyncio import AsyncSession
from domain.projects.service import ProjectService

from .dto import MetricDTO
from .dto import MetricCreateDTO, MetricUpdateDTO
from .error import MetricNotAccessibleError, MetricNotFoundError
from .mapper import MetricMapper
from .repository import MetricRepository


class MetricService:
    def __init__(
        self,
        db: AsyncSession,
        metric_repository: MetricRepository,
        experiment_repository: ExperimentRepository,
        permission_checker: PermissionChecker,
    ):
        self.db = db
        self.metric_repository = metric_repository
        self.experiment_repository = experiment_repository
        self.permission_checker = permission_checker
        self.metric_mapper = MetricMapper()

    async def _assert_can_view_metrics(
        self, user: UserProtocol, project_ids: Iterable[UUID_TYPE]
    ) -> None:
        for project_id in project_ids:
            if not await self.permission_checker.can_view_metric(user.id, project_id):
                raise MetricNotAccessibleError(f"Project {project_id} not accessible")

    async def get_metrics_by_experiment(
        self, user: UserProtocol, experiment_id: UUID_TYPE | list[UUID_TYPE]
    ) -> List[MetricDTO]:
        metrics = await self.metric_repository.get_metrics_by_experiment(
            experiment_id, full_load=True
        )
        project_ids = {
            metric.experiment.project_id
            for metric in metrics
            if metric.experiment is not None
        }
        if not project_ids and not isinstance(experiment_id, (list, tuple)):
            try:
                experiment = await self.experiment_repository.get_by_id(experiment_id)
            except DBNotFoundError as exc:
                raise MetricNotFoundError(
                    f"Experiment {experiment_id} not found"
                ) from exc
            project_ids = {experiment.project_id}
        await self._assert_can_view_metrics(user, project_ids)
        return self.metric_mapper.metric_list_schema_to_dto(metrics)

    async def create_metric(
        self, user: UserProtocol, data: MetricCreateDTO
    ) -> MetricDTO:
        try:
            experiment = await self.experiment_repository.get_by_id(data.experiment_id)
        except DBNotFoundError as exc:
            raise MetricNotFoundError(
                f"Experiment {data.experiment_id} not found"
            ) from exc
        if not await self.permission_checker.can_create_metric(
            user.id, experiment.project_id
        ):
            raise MetricNotAccessibleError(
                f"Project {experiment.project_id} not accessible"
            )
        metric = self.metric_mapper.metric_create_dto_to_schema(data)
        await self.metric_repository.create(metric)
        await self.db.commit()
        return self.metric_mapper.metric_schema_to_dto(metric)

    async def update_metric(
        self, user: UserProtocol, metric_id: UUID_TYPE, data: MetricUpdateDTO
    ) -> MetricDTO:
        try:
            metric = await self.metric_repository.get_by_id(metric_id)
        except DBNotFoundError as exc:
            raise MetricNotFoundError(f"Metric {metric_id} not found") from exc
        try:
            experiment = await self.experiment_repository.get_by_id(
                metric.experiment_id
            )
        except DBNotFoundError as exc:
            raise MetricNotFoundError(
                f"Experiment {metric.experiment_id} not found"
            ) from exc
        if not await self.permission_checker.can_edit_metric(
            user.id, experiment.project_id
        ):
            raise MetricNotAccessibleError(
                f"Project {experiment.project_id} not accessible"
            )
        updates = self.metric_mapper.metric_update_dto_to_update_dict(data)
        result = await self.metric_repository.update(metric_id, **updates)
        await self.db.commit()
        return self.metric_mapper.metric_schema_to_dto(result)

    async def delete_metric(self, user: UserProtocol, metric_id: UUID_TYPE) -> bool:
        try:
            metric = await self.metric_repository.get_by_id(metric_id)
        except DBNotFoundError as exc:
            raise MetricNotFoundError(f"Metric {metric_id} not found") from exc
        try:
            experiment = await self.experiment_repository.get_by_id(
                metric.experiment_id
            )
        except DBNotFoundError as exc:
            raise MetricNotFoundError(
                f"Experiment {metric.experiment_id} not found"
            ) from exc
        if not await self.permission_checker.can_delete_metric(
            user.id, experiment.project_id
        ):
            raise MetricNotAccessibleError(
                f"Project {experiment.project_id} not accessible"
            )
        await self.metric_repository.delete(metric_id)
        await self.db.commit()
        return True

    # TODO cover with tests
    async def get_aggregated_metrics_for_experiment(
        self, user: UserProtocol, experiment_id: UUID_TYPE
    ) -> List[MetricDTO]:

        metrics = await self.metric_repository.get_metrics_by_experiment(
            experiment_id, full_load=True
        )
        if not metrics:
            return []
        project_id = metrics[0].experiment.project_id
        if not await self.permission_checker.can_view_metric(user.id, project_id):
            raise MetricNotAccessibleError(f"Project {project_id} not accessible")
        return metrics

    async def get_aggregated_metrics_for_project(
        self, user: UserProtocol, project_id: UUID_TYPE, project_service: ProjectService
    ) -> List[MetricDTO]:

        if not await self.permission_checker.can_view_metric(user.id, project_id):
            raise MetricNotAccessibleError(f"Project {project_id} not accessible")
        # Get project metrics configuration
        project = await project_service.get_project_if_accessible(user, project_id)
        project_metrics = project.metrics

        # Get experiments and metrics
        experiment_repository = ExperimentRepository(self.db)
        experiments = await experiment_repository.get_experiments_by_project(
            project_id, full_load=["metrics"]
        )
        metrics = []
        for experiment in experiments:
            for project_metric in project_metrics:
                metric_name = project_metric.name
                matching_metrics = [
                    metric
                    for metric in experiment.metrics
                    if metric.name == metric_name
                ]
                if not matching_metrics:
                    continue

                aggregation_str = project_metric.aggregation
                direction_str = project_metric.direction
                if aggregation_str == MetricAggregation.LAST:
                    metric = max(matching_metrics, key=lambda m: m.step)
                elif (
                    aggregation_str == MetricAggregation.BEST
                    and direction_str == MetricDirection.MAXIMIZE
                ):
                    metric = max(matching_metrics, key=lambda m: m.value)
                elif (
                    aggregation_str == MetricAggregation.BEST
                    and direction_str == MetricDirection.MINIMIZE
                ):
                    metric = min(matching_metrics, key=lambda m: m.value)
                elif aggregation_str == MetricAggregation.AVERAGE:
                    raise NotImplementedError(f"AVERAGE aggregation is not supported")
                    # metric = sum(metrics, key=lambda m: m.value) / len(metrics)
                else:
                    raise ValueError(f"Invalid aggregation: {aggregation_str}")

                metrics.append(self.metric_mapper.metric_schema_to_dto(metric))
        return metrics
