from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/projects")
async def get_all_projects(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await repository.get_accessible_projects(session, user)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    project = await repository.get_project_if_accessible(session, user, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    from .repository import _project_to_schema

    return _project_to_schema(project)


@router.get("/projects/{project_id}/experiments")
async def get_project_experiments(
    project_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await repository.get_experiments_by_project(session, user, project_id)


@router.get("/projects/{project_id}/hypotheses")
async def get_project_hypotheses(
    project_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await repository.get_hypotheses_by_project(session, user, project_id)


@router.get("/projects/{project_id}/metrics")
async def get_project_metrics(
    project_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await repository.get_aggregated_metrics_for_project(
        session, user, project_id
    )


@router.post("/projects")
async def create_project(
    data: ProjectCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await repository.create_project(session, user, data, data.teamId)


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await repository.update_project(session, user, project_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    success = await repository.delete_project(session, user, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}
