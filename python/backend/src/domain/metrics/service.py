from typing import Dict, Iterable, List, Tuple

from domain.experiments.repository import ExperimentRepository
from domain.rbac.wrapper import PermissionChecker
from lib.db.base_repository import DBNotFoundError
from lib.pagination import ListOptions, paginate_sequence
from lib.protocols.user_protocol import UserProtocol
from lib.types import UUID_TYPE
from models import Metric, MetricAggregation, MetricDirection
from sqlalchemy.ext.asyncio import AsyncSession
from domain.projects.service import ProjectService

from .dto import (
    MetricDTO,
    MetricLabelsResponseDTO,
    MetricListResponseDTO,
    MetricsByLabelRowDTO,
    MetricsByLabelSnapshotResponseDTO,
    MetricUpsertDTO,
    UniqueMetricDimensionDTO,
    UniqueMetricDimensionsResponseDTO,
)
from .error import MetricNotAccessibleError, MetricNotFoundError
from .mapper import MetricMapper
from .repository import MetricRepository


class MetricService:
    """Application service for metric definitions stored in Postgres.

    The service handles experiment-scoped metric CRUD, project-wide metric summary
    views, and dashboard aggregation helpers. Every public method validates the
    caller's project permission before returning or mutating metric data.
    """

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

    @staticmethod
    def _normalize_upsert_dto_label(data: MetricUpsertDTO) -> MetricUpsertDTO:
        """Treat empty label like None (validators skipped by model_construct / internal callers)."""
        if data.label != "":
            return data
        return data.model_copy(update={"label": None})

    async def _assert_can_view_metrics(
        self, user: UserProtocol, project_ids: Iterable[UUID_TYPE]
    ) -> None:
        for project_id in project_ids:
            if not await self.permission_checker.can_view_metric(user.id, project_id):
                raise MetricNotAccessibleError(f"Project {project_id} not accessible")

    async def get_metrics_by_experiment(
        self,
        user: UserProtocol,
        experiment_id: UUID_TYPE | list[UUID_TYPE],
        list_options: ListOptions = ListOptions(),
    ) -> MetricListResponseDTO:
        """List metrics for one or more experiments.

        Args:
            user: User requesting metrics.
            experiment_id: Single experiment id or list of experiment ids.
            list_options: Pagination limit and offset.

        Returns:
            MetricListResponseDTO: Paginated metric DTOs.

        Raises:
            MetricNotFoundError: If a single requested experiment does not exist.
            MetricNotAccessibleError: If the user cannot view metrics in any owning
                project represented by the returned rows.
        """
        metrics_page = await self.metric_repository.get_metrics_by_experiment(
            experiment_id,
            full_load=True,
            list_options=list_options,
        )
        project_ids = {
            metric.experiment.project_id
            for metric in metrics_page.data
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
        return MetricListResponseDTO.from_page(
            metrics_page.map(self.metric_mapper.metric_schema_to_dto)
        )

    async def get_metric_by_key(
        self,
        user: UserProtocol,
        experiment_id: UUID_TYPE,
        name: str,
        label: str | None,
    ) -> MetricDTO:
        """Get a metric by its natural experiment/name/label key.

        Args:
            user: User requesting the metric.
            experiment_id: Experiment that owns the metric.
            name: Metric name.
            label: Optional label; empty string maps to the unlabeled ``NULL`` label.

        Returns:
            MetricDTO: Matching metric DTO.

        Raises:
            MetricNotFoundError: If the experiment or metric key is missing.
            MetricNotAccessibleError: If the user cannot view metrics in the
                experiment's project.
        """
        try:
            experiment = await self.experiment_repository.get_by_id(experiment_id)
        except DBNotFoundError as exc:
            raise MetricNotFoundError(f"Experiment {experiment_id} not found") from exc
        if not await self.permission_checker.can_view_metric(
            user.id, experiment.project_id
        ):
            raise MetricNotAccessibleError(
                f"Project {experiment.project_id} not accessible"
            )
        metric = await self.metric_repository.get_by_experiment_name_and_label(
            experiment_id,
            name,
            None if label == "" else label,
        )
        if metric is None:
            raise MetricNotFoundError(
                f"Metric not found for experiment={experiment_id} name={name!r} label={label!r}"
            )
        return self.metric_mapper.metric_schema_to_dto(metric)

    async def upsert_metric(self, user: UserProtocol, data: MetricUpsertDTO) -> MetricDTO:
        """Create or update a metric for an experiment.

        Existing rows are matched by ``experiment_id``, ``name``, and normalized
        ``label``. Updating an existing metric requires edit permission; inserting a
        new metric requires create permission.

        Args:
            user: User performing the write.
            data: Metric upsert payload.

        Returns:
            MetricDTO: Persisted metric DTO after commit.

        Raises:
            MetricNotFoundError: If the target experiment does not exist.
            MetricNotAccessibleError: If the user lacks the required create or edit
                permission for the experiment's project.
        """
        data = self._normalize_upsert_dto_label(data)
        try:
            experiment = await self.experiment_repository.get_by_id(data.experiment_id)
        except DBNotFoundError as exc:
            raise MetricNotFoundError(
                f"Experiment {data.experiment_id} not found"
            ) from exc
        project_id = experiment.project_id
        existing = await self.metric_repository.get_by_experiment_name_and_label(
            data.experiment_id, data.name, data.label
        )
        if existing is not None:
            if not await self.permission_checker.can_edit_metric(user.id, project_id):
                raise MetricNotAccessibleError(
                    f"Project {project_id} not accessible"
                )
            result = await self.metric_repository.update(
                existing.id, value=data.value
            )
            await self.db.commit()
            return self.metric_mapper.metric_schema_to_dto(result)
        if not await self.permission_checker.can_create_metric(user.id, project_id):
            raise MetricNotAccessibleError(
                f"Project {project_id} not accessible"
            )
        metric = self.metric_mapper.metric_upsert_dto_to_schema(data)
        await self.metric_repository.create(metric)
        await self.db.commit()
        return self.metric_mapper.metric_schema_to_dto(metric)

    async def delete_metric(self, user: UserProtocol, metric_id: UUID_TYPE) -> bool:
        """Delete a metric row.

        Args:
            user: User deleting the metric.
            metric_id: Metric identifier.

        Returns:
            bool: ``True`` after the delete and commit succeed.

        Raises:
            MetricNotFoundError: If the metric or owning experiment is missing.
            MetricNotAccessibleError: If the user cannot delete metrics in the
                owning project.
        """
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
        self,
        user: UserProtocol,
        experiment_id: UUID_TYPE,
        list_options: ListOptions = ListOptions(),
    ) -> MetricListResponseDTO:
        """Return metric rows for an experiment in list-display shape.

        Args:
            user: User requesting the metrics.
            experiment_id: Experiment whose metrics should be listed.
            list_options: Pagination limit and offset.

        Returns:
            MetricListResponseDTO: Paginated metrics, or an empty page when the
            experiment has no metrics.

        Raises:
            MetricNotAccessibleError: If metrics exist but the user cannot view the
                owning project.
        """

        metrics_page = await self.metric_repository.get_metrics_by_experiment(
            experiment_id,
            full_load=True,
            list_options=list_options,
        )
        if not metrics_page.data:
            return MetricListResponseDTO(
                data=[], has_next=False, size=0, total=metrics_page.total
            )
        project_id = metrics_page.data[0].experiment.project_id
        if not await self.permission_checker.can_view_metric(user.id, project_id):
            raise MetricNotAccessibleError(f"Project {project_id} not accessible")
        return MetricListResponseDTO.from_page(
            metrics_page.map(self.metric_mapper.metric_schema_to_dto)
        )

    async def get_aggregated_metrics_for_project(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        project_service: ProjectService,
        list_options: ListOptions = ListOptions(),
    ) -> MetricListResponseDTO:
        """Aggregate configured project metrics across experiments.

        Uses the project's tracked metric configuration to choose one metric per
        experiment/configured metric pair, applying ``LAST`` or ``BEST`` according to
        the configured direction.

        Args:
            user: User requesting project metrics.
            project_id: Project whose tracked metrics should be aggregated.
            project_service: Project service used to load project configuration.
            list_options: Pagination options applied after aggregation.

        Returns:
            MetricListResponseDTO: Paginated aggregate metric rows.

        Raises:
            MetricNotAccessibleError: If the user cannot view metrics in the project.
            NotImplementedError: If a configured metric uses ``AVERAGE`` aggregation.
            ValueError: If a metric configuration contains an unknown aggregation.
        """

        if not await self.permission_checker.can_view_metric(user.id, project_id):
            raise MetricNotAccessibleError(f"Project {project_id} not accessible")
        # Get project metrics configuration
        project = await project_service.get_project_if_accessible(user, project_id)
        project_metrics = project.metrics.tracked_metrics

        # Get experiments and metrics
        experiment_repository = ExperimentRepository(self.db)
        experiments = (
            await experiment_repository.get_experiments_by_project(
                project_id, full_load=["metrics"]
            )
        ).data
        metrics = []
        for experiment in experiments:
            for project_metric in project_metrics:
                metric_name = project_metric.name
                pm_label = project_metric.label
                if pm_label is None:
                    matching_metrics = [
                        m
                        for m in experiment.metrics
                        if m.name == metric_name
                    ]
                else:
                    matching_metrics = [
                        m
                        for m in experiment.metrics
                        if m.name == metric_name and m.label == pm_label
                    ]
                if not matching_metrics:
                    continue

                aggregation_str = project_metric.aggregation
                direction_str = project_metric.direction
                if aggregation_str == MetricAggregation.LAST:
                    metric = max(matching_metrics, key=lambda m: m.created_at)
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
        paginated_metrics = paginate_sequence(metrics, list_options)
        return MetricListResponseDTO.from_page(paginated_metrics)

    @staticmethod
    def _parse_label_param(label: str) -> str | None:
        """Query `label` uses empty string for unlabeled (NULL) metrics in DB."""
        return None if label == "" else label

    async def get_metric_labels_for_project(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> MetricLabelsResponseDTO:
        """List distinct metric labels for a project.

        Args:
            user: User requesting label metadata.
            project_id: Project whose metric labels should be inspected.

        Returns:
            MetricLabelsResponseDTO: Distinct non-null labels plus an ``has_unlabeled``
            flag for ``NULL`` labels.

        Raises:
            MetricNotAccessibleError: If the user cannot view project metrics.
        """
        if not await self.permission_checker.can_view_metric(user.id, project_id):
            raise MetricNotAccessibleError(f"Project {project_id} not accessible")
        labels, has_unlabeled = await self.metric_repository.list_distinct_labels_in_project(
            project_id
        )
        return MetricLabelsResponseDTO(labels=labels, has_unlabeled=has_unlabeled)

    async def get_unique_metric_dimensions_for_project(
        self, user: UserProtocol, project_id: UUID_TYPE
    ) -> UniqueMetricDimensionsResponseDTO:
        """List unique metric ``name``/``label`` pairs for a project.

        Args:
            user: User requesting dimension metadata.
            project_id: Project whose metrics should be scanned.

        Returns:
            UniqueMetricDimensionsResponseDTO: Unique metric dimensions available for
            charts and filters.

        Raises:
            MetricNotAccessibleError: If the user cannot view project metrics.
        """
        if not await self.permission_checker.can_view_metric(user.id, project_id):
            raise MetricNotAccessibleError(f"Project {project_id} not accessible")
        pairs = await self.metric_repository.list_unique_name_label_in_project(project_id)
        return UniqueMetricDimensionsResponseDTO(
            items=[UniqueMetricDimensionDTO(name=n, label=l) for n, l in pairs]
        )

    async def get_metrics_by_label_snapshot(
        self,
        user: UserProtocol,
        project_id: UUID_TYPE,
        label: str,
        include_experiments_without_metrics: bool,
        list_options: ListOptions,
    ) -> MetricsByLabelSnapshotResponseDTO:
        """Build a latest-value metric table for one label.

        Args:
            user: User requesting the snapshot.
            project_id: Project whose experiments should be included.
            label: Label filter; empty string selects unlabeled metrics.
            include_experiments_without_metrics: Whether to include experiments with
                no metric for the selected label.
            list_options: Pagination options applied to experiment rows.

        Returns:
            MetricsByLabelSnapshotResponseDTO: Metric names and one row per selected
            experiment with latest values by metric name.

        Raises:
            MetricNotAccessibleError: If the user cannot view project metrics.
        """
        if not await self.permission_checker.can_view_metric(user.id, project_id):
            raise MetricNotAccessibleError(f"Project {project_id} not accessible")
        plabel = self._parse_label_param(label)
        all_rows = await self.metric_repository.list_metrics_for_project_label(
            project_id, plabel
        )
        metric_names = sorted({m.name for m in all_rows})
        if not metric_names:
            return MetricsByLabelSnapshotResponseDTO(
                metric_names=[],
                rows=[],
                has_next=False,
                total=0,
            )
        ex_with_metric: set[UUID_TYPE] = {m.experiment_id for m in all_rows}
        latest: Dict[Tuple[UUID_TYPE, str], Metric] = {}
        for m in all_rows:
            k = (m.experiment_id, m.name)
            if k not in latest or m.created_at > latest[k].created_at:
                latest[k] = m

        ordered_ids = await self.experiment_repository.list_experiment_ids_for_project_by_created_at_desc(
            project_id
        )
        if include_experiments_without_metrics:
            page_ids = ordered_ids[
                list_options.offset : list_options.offset + list_options.limit
            ]
            total = len(ordered_ids)
        else:
            filtered = [eid for eid in ordered_ids if eid in ex_with_metric]
            page_ids = filtered[
                list_options.offset : list_options.offset + list_options.limit
            ]
            total = len(filtered)
        if not page_ids:
            return MetricsByLabelSnapshotResponseDTO(
                metric_names=metric_names,
                rows=[],
                has_next=False,
                total=total,
            )
        experiments = await self.experiment_repository.get_experiments_by_ids(page_ids)
        by_id = {e.id: e for e in experiments}
        out_rows: List[MetricsByLabelRowDTO] = []
        for eid in page_ids:
            exp = by_id.get(eid)
            if exp is None:
                continue
            values: list[float | None] = []
            for name in metric_names:
                cell = latest.get((eid, name))
                values.append(None if cell is None else float(cell.value))
            out_rows.append(
                MetricsByLabelRowDTO(
                    experiment_id=exp.id,
                    experiment_name=exp.name,
                    created_at=exp.created_at,
                    color=exp.color,
                    values=values,
                )
            )
        has_next = list_options.offset + list_options.limit < total
        return MetricsByLabelSnapshotResponseDTO(
            metric_names=metric_names,
            rows=out_rows,
            has_next=has_next,
            total=total,
        )
