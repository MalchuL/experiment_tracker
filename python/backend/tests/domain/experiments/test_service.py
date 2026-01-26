from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.experiments.dto import ExperimentCreateDTO, ExperimentUpdateDTO
from domain.experiments.error import ExperimentNotAccessibleError
from domain.experiments.service import ExperimentService
from domain.experiments.utils import DEFAULT_EXPERIMENT_NAME_PATTERN
from domain.projects.errors import ProjectNotAccessibleError
from domain.rbac.permissions.project import ProjectActions
from domain.rbac.service import PermissionService
from lib.db.error import DBNotFoundError
from models import Experiment, ExperimentStatus, Project, User


async def _create_project(
    db_session: AsyncSession,
    owner: User,
    name: str = "Service Project",
    naming_pattern: str = DEFAULT_EXPERIMENT_NAME_PATTERN,
) -> Project:
    project = Project(
        name=name,
        description="Experiment service project",
        owner_id=owner.id,
        team_id=None,
        metrics=[],
        settings={"naming_pattern": naming_pattern, "display_metrics": []},
    )
    db_session.add(project)
    await db_session.flush()
    print(project.id, project.metrics)
    await db_session.refresh(project)
    return project


async def _create_experiment(
    db_session: AsyncSession,
    project: Project,
    name: str,
    status: ExperimentStatus = ExperimentStatus.PLANNED,
    order: int = 0,
    started_by: User | None = None,
    created_at: datetime | None = None,
) -> Experiment:
    experiment = Experiment(
        id=None,
        project_id=project.id,
        name=name,
        description="Service experiment",
        status=status,
        order=order,
        started_by=started_by.id if started_by else None,
        created_at=created_at,
    )
    db_session.add(experiment)
    await db_session.flush()
    # await db_session.commit()
    return experiment


class TestExperimentService:
    @pytest.fixture
    def experiment_service(self, db_session: AsyncSession) -> ExperimentService:
        return ExperimentService(db_session)

    async def test_parse_experiment_name_from_project_requires_access(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        with pytest.raises(ProjectNotAccessibleError):
            await experiment_service.parse_experiment_name_from_project(
                test_user, project.id, "1_from_root_seed"
            )

    async def test_parse_experiment_name_from_project(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_EXPERIMENT,
            allowed=True,
            project_id=project.id,
        )

        result = await experiment_service.parse_experiment_name_from_project(
            test_user, project.id, "1_from_root_seed"
        )

        assert result.num == "1"
        assert result.parent == "root"
        assert result.change == "seed"

    async def test_get_parent_id_if_accessible(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        parent = await _create_experiment(db_session, project, "1_from_root_seed")
        await _create_experiment(db_session, project, "2_from_1_seed")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_EXPERIMENT,
            allowed=True,
            project_id=project.id,
        )

        parent_id = await experiment_service.get_parent_id_if_accessible(
            test_user, project.id, "2_from_1_seed"
        )

        assert parent_id == parent.id

    async def test_get_recent_experiments_limits_and_orders(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        await _create_experiment(
            db_session,
            project,
            name="Older",
            started_by=test_user,
            created_at=datetime(2024, 1, 1),
        )
        await _create_experiment(
            db_session,
            project,
            name="Newer",
            started_by=test_user,
            created_at=datetime(2024, 1, 2),
        )

        recent = await experiment_service.get_recent_experiments(test_user, limit=1)

        assert len(recent) == 1
        assert recent[0].name == "Newer"

    async def test_get_experiment_if_accessible_requires_permission(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")

        with pytest.raises(ExperimentNotAccessibleError):
            await experiment_service.get_experiment_if_accessible(
                test_user, experiment.id
            )

    async def test_create_experiment_permission_denied(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        dto = ExperimentCreateDTO(
            project_id=project.id,
            name="Denied",
            description="Denied",
            parent_experiment_name=None,
        )

        with pytest.raises(ExperimentNotAccessibleError):
            await experiment_service.create_experiment(test_user, dto)

    async def test_create_experiment_sets_parent_from_name(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        assert db_session is experiment_service.experiment_repository.db
        project = await _create_project(db_session, test_user)
        parent = await _create_experiment(db_session, project, "1_from_root_seed")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.CREATE_EXPERIMENT,
            allowed=True,
            project_id=project.id,
        )
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_EXPERIMENT,
            allowed=True,
            project_id=project.id,
        )
        dto = ExperimentCreateDTO(
            project_id=project.id,
            name="2_from_1_seed",
            description="Child",
            parent_experiment_name="2_from_1_seed",
        )

        created = await experiment_service.create_experiment(test_user, dto)

        assert created.parent_experiment_id == parent.id

    async def test_update_experiment_permission_denied(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        dto = ExperimentUpdateDTO(name="Updated", description=None)

        with pytest.raises(ExperimentNotAccessibleError):
            await experiment_service.update_experiment(test_user, experiment.id, dto)

    async def test_update_experiment_updates_fields(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.EDIT_EXPERIMENT,
            allowed=True,
            project_id=project.id,
        )
        dto = ExperimentUpdateDTO(
            name="Updated", description="Updated description", progress=50
        )

        updated = await experiment_service.update_experiment(
            test_user, experiment.id, dto
        )

        assert updated.name == "Updated"
        assert updated.progress == 50

    async def test_delete_experiment_permission_denied(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")

        with pytest.raises(ExperimentNotAccessibleError):
            await experiment_service.delete_experiment(test_user, experiment.id)

    async def test_delete_experiment_removes_experiment(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        experiment = await _create_experiment(db_session, project, "Experiment")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.DELETE_EXPERIMENT,
            allowed=True,
            project_id=project.id,
        )

        deleted = await experiment_service.delete_experiment(test_user, experiment.id)

        assert deleted is True
        assert await db_session.get(Experiment, experiment.id) is None

    async def test_reorder_experiments_updates_order(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        exp_a = await _create_experiment(db_session, project, "A", order=0)
        exp_b = await _create_experiment(db_session, project, "B", order=1)
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.EDIT_EXPERIMENT,
            allowed=True,
            project_id=project.id,
        )

        result = await experiment_service.reorder_experiments(
            test_user, project.id, [exp_b.id, exp_a.id]
        )

        assert result is True
        refreshed_a = await db_session.get(Experiment, exp_a.id)
        refreshed_b = await db_session.get(Experiment, exp_b.id)
        assert refreshed_a is not None
        assert refreshed_b is not None
        assert refreshed_a.order == 1
        assert refreshed_b.order == 0

    async def test_get_experiment_if_accessible_missing_experiment_raises(
        self,
        experiment_service: ExperimentService,
        test_user: User,
    ) -> None:
        with pytest.raises(DBNotFoundError):
            await experiment_service.get_experiment_if_accessible(test_user, uuid4())

    async def test_get_experiments_by_project_requires_permission(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        await _create_experiment(db_session, project, "Experiment")

        with pytest.raises(ExperimentNotAccessibleError):
            await experiment_service.get_experiments_by_project(test_user, project.id)

    async def test_get_experiments_by_project_returns_list(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        exp_a = await _create_experiment(db_session, project, "Experiment A")
        exp_b = await _create_experiment(db_session, project, "Experiment B")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_EXPERIMENT,
            allowed=True,
            project_id=project.id,
        )

        experiments = await experiment_service.get_experiments_by_project(
            test_user, project.id
        )

        experiment_ids = {experiment.id for experiment in experiments}
        assert experiment_ids == {exp_a.id, exp_b.id}
