from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.hypotheses.dto import HypothesisCreateDTO, HypothesisUpdateDTO
from domain.hypotheses.error import (
    HypothesisNotAccessibleError,
    HypothesisNotFoundError,
)
from domain.hypotheses.service import HypothesisService
from domain.projects.errors import ProjectNotAccessibleError
from domain.rbac.permissions import ProjectActions
from domain.rbac.service import PermissionService
from models import Hypothesis, HypothesisStatus, Project, User


async def _create_project(
    db_session: AsyncSession, owner: User, name: str = "Service Project"
) -> Project:
    project = Project(
        name=name,
        description="Hypothesis service project",
        owner_id=owner.id,
        team_id=None,
        metrics=[],
        settings={},
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


async def _create_hypothesis(
    db_session: AsyncSession,
    project: Project,
    title: str,
    status: HypothesisStatus = HypothesisStatus.PROPOSED,
) -> Hypothesis:
    hypothesis = Hypothesis(
        id=None,
        project_id=project.id,
        title=title,
        description="Service hypothesis",
        author="Service Author",
        status=status,
        target_metrics=["accuracy"],
        baseline="root",
    )
    db_session.add(hypothesis)
    await db_session.flush()
    return hypothesis


class TestHypothesisService:
    @pytest.fixture
    def hypothesis_service(self, db_session: AsyncSession) -> HypothesisService:
        return HypothesisService(db_session)

    async def test_get_hypotheses_by_project_requires_access(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)

        with pytest.raises(ProjectNotAccessibleError):
            await hypothesis_service.get_hypotheses_by_project(test_user, project.id)

    async def test_get_hypotheses_by_project_returns_list(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        await _create_hypothesis(db_session, project, "H1")
        await _create_hypothesis(db_session, project, "H2")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_HYPOTHESIS,
            allowed=True,
            project_id=project.id,
        )

        hypotheses = await hypothesis_service.get_hypotheses_by_project(
            test_user, project.id
        )

        titles = {hypothesis.title for hypothesis in hypotheses}
        assert titles == {"H1", "H2"}

    async def test_get_hypothesis_if_accessible_requires_permission(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        hypothesis = await _create_hypothesis(db_session, project, "Hypothesis")

        with pytest.raises(HypothesisNotAccessibleError):
            await hypothesis_service.get_hypothesis_if_accessible(
                test_user, hypothesis.id
            )

    async def test_get_hypothesis_if_accessible_missing_raises(
        self,
        hypothesis_service: HypothesisService,
        test_user: User,
    ) -> None:
        with pytest.raises(HypothesisNotFoundError):
            await hypothesis_service.get_hypothesis_if_accessible(test_user, uuid4())

    async def test_get_hypothesis_if_accessible_returns_dto(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        hypothesis = await _create_hypothesis(db_session, project, "Hypothesis")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.VIEW_HYPOTHESIS,
            allowed=True,
            project_id=project.id,
        )

        result = await hypothesis_service.get_hypothesis_if_accessible(
            test_user, hypothesis.id
        )

        assert result.id == hypothesis.id
        assert result.title == "Hypothesis"

    async def test_create_hypothesis_permission_denied(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        dto = HypothesisCreateDTO(
            project_id=project.id,
            title="Denied",
            description="Denied",
            author="Author",
            status=HypothesisStatus.PROPOSED,
            target_metrics=["accuracy"],
            baseline="root",
        )

        with pytest.raises(HypothesisNotAccessibleError):
            await hypothesis_service.create_hypothesis(test_user, dto)

    async def test_create_hypothesis_sets_fields(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.CREATE_HYPOTHESIS,
            allowed=True,
            project_id=project.id,
        )
        dto = HypothesisCreateDTO(
            project_id=project.id,
            title="Created",
            description="Created description",
            author="Author",
            status=HypothesisStatus.TESTING,
            target_metrics=["accuracy"],
            baseline="root",
        )

        created = await hypothesis_service.create_hypothesis(test_user, dto)

        assert created.id is not None
        assert created.project_id == project.id
        assert created.title == "Created"
        assert created.status == HypothesisStatus.TESTING

    async def test_update_hypothesis_permission_denied(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        hypothesis = await _create_hypothesis(db_session, project, "Hypothesis")
        dto = HypothesisUpdateDTO(title="Updated")

        with pytest.raises(HypothesisNotAccessibleError):
            await hypothesis_service.update_hypothesis(test_user, hypothesis.id, dto)

    async def test_update_hypothesis_updates_fields(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        hypothesis = await _create_hypothesis(db_session, project, "Hypothesis")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.EDIT_HYPOTHESIS,
            allowed=True,
            project_id=project.id,
        )
        dto = HypothesisUpdateDTO(
            title="Updated",
            description="Updated description",
            status=HypothesisStatus.SUPPORTED,
        )

        updated = await hypothesis_service.update_hypothesis(
            test_user, hypothesis.id, dto
        )

        assert updated.title == "Updated"
        assert updated.status == HypothesisStatus.SUPPORTED

    async def test_update_hypothesis_missing_raises(
        self, hypothesis_service: HypothesisService, test_user: User
    ) -> None:
        dto = HypothesisUpdateDTO(title="Updated")
        with pytest.raises(HypothesisNotFoundError):
            await hypothesis_service.update_hypothesis(test_user, uuid4(), dto)

    async def test_delete_hypothesis_permission_denied(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        hypothesis = await _create_hypothesis(db_session, project, "Hypothesis")

        with pytest.raises(HypothesisNotAccessibleError):
            await hypothesis_service.delete_hypothesis(test_user, hypothesis.id)

    async def test_delete_hypothesis_removes_hypothesis(
        self,
        hypothesis_service: HypothesisService,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        project = await _create_project(db_session, test_user)
        hypothesis = await _create_hypothesis(db_session, project, "Hypothesis")
        permission_service = PermissionService(db_session, auto_commit=True)
        await permission_service.add_permission(
            user_id=test_user.id,
            action=ProjectActions.DELETE_HYPOTHESIS,
            allowed=True,
            project_id=project.id,
        )

        deleted = await hypothesis_service.delete_hypothesis(test_user, hypothesis.id)

        assert deleted is True
        assert await db_session.get(Hypothesis, hypothesis.id) is None
