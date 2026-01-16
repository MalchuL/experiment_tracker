"""
Tests for ExperimentService.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.experiments.dto import ExperimentCreateDTO, ExperimentUpdateDTO
from domain.experiments.error import ExperimentNotAccessibleError
from domain.experiments.service import ExperimentService
from domain.experiments.utils import DEFAULT_EXPERIMENT_NAME_PATTERN
from domain.projects.errors import ProjectNotAccessibleError
from models import Experiment, ExperimentStatus, Project, User


class TestExperimentService:
    """Test suite for ExperimentService."""

    @pytest.fixture(scope="function")
    def experiment_service(self, db_session: AsyncSession) -> ExperimentService:
        """Create an ExperimentService instance."""
        return ExperimentService(db_session)

    async def _create_project(
        self,
        db_session: AsyncSession,
        owner: User,
        naming_pattern: str = DEFAULT_EXPERIMENT_NAME_PATTERN,
    ) -> Project:
        project = Project(
            id=None,
            name="Test Project",
            description="Test description",
            owner_id=owner.id,
            team_id=None,
            settings={
                "naming_pattern": naming_pattern,
                "display_metrics": [],
            },
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)
        return project

    async def _create_experiment(
        self,
        db_session: AsyncSession,
        project: Project,
        name: str,
        status: ExperimentStatus = ExperimentStatus.PLANNED,
        order: int = 0,
    ) -> Experiment:
        experiment = Experiment(
            id=None,
            project_id=project.id,
            name=name,
            description="Experiment description",
            status=status,
            order=order,
        )
        db_session.add(experiment)
        await db_session.flush()
        await db_session.refresh(experiment)
        return experiment

    async def test_parse_experiment_name(self, experiment_service: ExperimentService):
        """Test parsing an experiment name."""
        result = await experiment_service.parse_experiment_name(
            "1_from_root_seed", DEFAULT_EXPERIMENT_NAME_PATTERN
        )
        assert result.num == "1"
        assert result.parent == "root"
        assert result.change == "seed"

    async def test_parse_experiment_name_from_project(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test parsing experiment name using project naming pattern."""
        project = await self._create_project(
            db_session,
            test_user,
            naming_pattern="{num}-from-{parent}-{change}",
        )
        result = await experiment_service.parse_experiment_name_from_project(
            test_user, project.id, "2-from-root-change"
        )
        assert result.num == "2"
        assert result.parent == "root"
        assert result.change == "change"

    async def test_parse_experiment_name_from_project_not_accessible(
        self,
        experiment_service: ExperimentService,
        test_user: User,
    ):
        """Test parsing experiment name for inaccessible project raises error."""
        with pytest.raises(
            ProjectNotAccessibleError, match="Project .* not accessible"
        ):
            await experiment_service.parse_experiment_name_from_project(
                test_user, uuid4(), "1_from_root_seed"
            )

    async def test_get_parent_id_if_accessible(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test resolving a parent experiment id by name."""
        project = await self._create_project(db_session, test_user)
        parent = await self._create_experiment(db_session, project, "1_from_root_seed")

        parent_id = await experiment_service.get_parent_id_if_accessible(
            test_user, project.id, "2_from_1_change"
        )
        assert parent_id == parent.id

    async def test_get_parent_id_if_accessible_no_parent(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test resolving parent id when no experiments exist returns None."""
        project = await self._create_project(db_session, test_user)
        parent_id = await experiment_service.get_parent_id_if_accessible(
            test_user, project.id, "2_from_1_change"
        )
        assert parent_id is None

    async def test_get_parent_id_if_accessible_not_accessible(
        self,
        experiment_service: ExperimentService,
        test_user: User,
    ):
        """Test resolving parent id for inaccessible project raises error."""
        with pytest.raises(
            ProjectNotAccessibleError, match="Project .* not accessible"
        ):
            await experiment_service.get_parent_id_if_accessible(
                test_user, uuid4(), "2_from_1_change"
            )

    async def test_create_experiment_success(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test creating an experiment in an accessible project."""
        project = await self._create_project(db_session, test_user)
        create_dto = ExperimentCreateDTO(
            projectId=str(project.id),
            name="1_from_root_seed",
            description="Experiment description",
            status=ExperimentStatus.PLANNED,
        )

        result = await experiment_service.create_experiment(test_user, create_dto)

        assert result.id is not None
        assert str(result.project_id) == str(project.id)
        assert result.name == "1_from_root_seed"
        assert result.description == "Experiment description"
        assert result.status == ExperimentStatus.PLANNED

    async def test_create_experiment_not_accessible(
        self,
        experiment_service: ExperimentService,
        test_user: User,
    ):
        """Test creating an experiment for inaccessible project raises error."""
        create_dto = ExperimentCreateDTO(
            projectId=str(uuid4()),
            name="1_from_root_seed",
            description="Experiment description",
            status=ExperimentStatus.PLANNED,
        )
        with pytest.raises(
            ProjectNotAccessibleError, match="Project .* not accessible"
        ):
            await experiment_service.create_experiment(test_user, create_dto)

    async def test_update_experiment_success(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test updating an experiment."""
        project = await self._create_project(db_session, test_user)
        experiment = await self._create_experiment(
            db_session, project, "1_from_root_seed"
        )
        update_dto = ExperimentUpdateDTO(
            name="1_from_root_updated", status=ExperimentStatus.RUNNING
        )

        result = await experiment_service.update_experiment(
            test_user, experiment.id, update_dto
        )

        assert result.id == experiment.id
        assert result.name == "1_from_root_updated"
        assert result.status == ExperimentStatus.RUNNING

    async def test_update_experiment_not_accessible(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test updating an inaccessible experiment raises error."""
        project = await self._create_project(db_session, test_user_2)
        experiment = await self._create_experiment(
            db_session, project, "1_from_root_seed"
        )
        update_dto = ExperimentUpdateDTO(name="Updated")

        with pytest.raises(
            ExperimentNotAccessibleError,
            match=f"Experiment {experiment.id} not accessible",
        ):
            await experiment_service.update_experiment(
                test_user, experiment.id, update_dto
            )

    async def test_delete_experiment_success(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting an experiment."""
        project = await self._create_project(db_session, test_user)
        experiment = await self._create_experiment(
            db_session, project, "1_from_root_seed"
        )

        result = await experiment_service.delete_experiment(test_user, experiment.id)
        assert result is True

        fetched = await experiment_service.get_experiment_if_accessible(
            test_user, experiment.id
        )
        assert fetched is None

    async def test_delete_experiment_not_accessible(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
        test_user_2: User,
    ):
        """Test deleting an inaccessible experiment raises error."""
        project = await self._create_project(db_session, test_user_2)
        experiment = await self._create_experiment(
            db_session, project, "1_from_root_seed"
        )
        with pytest.raises(
            ExperimentNotAccessibleError,
            match=f"Experiment {experiment.id} not accessible",
        ):
            await experiment_service.delete_experiment(test_user, experiment.id)

    async def test_reorder_experiments_success(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test reordering experiments updates order values."""
        project = await self._create_project(db_session, test_user)
        experiment1 = await self._create_experiment(
            db_session, project, "1_from_root_seed", order=0
        )
        experiment2 = await self._create_experiment(
            db_session, project, "2_from_1_change", order=1
        )

        result = await experiment_service.reorder_experiments(
            test_user, project.id, [experiment2.id, experiment1.id]
        )
        assert result is True

        updated_1 = await experiment_service.experiment_repository.get_by_id(
            experiment1.id
        )
        updated_2 = await experiment_service.experiment_repository.get_by_id(
            experiment2.id
        )
        assert updated_2.order == 0
        assert updated_1.order == 1

    async def test_reorder_experiments_no_experiments(
        self,
        experiment_service: ExperimentService,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test reordering with no experiments raises error."""
        project = await self._create_project(db_session, test_user)
        with pytest.raises(
            ExperimentNotAccessibleError,
            match=f"Project {project.id} not accessible",
        ):
            await experiment_service.reorder_experiments(test_user, project.id, [])
