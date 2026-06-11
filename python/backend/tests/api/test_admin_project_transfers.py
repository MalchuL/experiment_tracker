from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import create_app
from db.database import get_async_session
from models import Project, Team, User


async def test_admin_moves_project_and_changes_standalone_owner(
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
) -> None:
    app: FastAPI = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_db
    client = TestClient(app)
    headers = {"X-Admin-Key": "admin"}

    project = Project(name="Admin transfer", description="", owner_id=test_user.id)
    team = Team(name="Admin destination", description="", owner_id=test_user_2.id)
    db_session.add_all([project, team])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(team)

    move = client.patch(
        f"/api/admin/projects/{project.id}/team",
        headers=headers,
        json={"teamId": str(team.id)},
    )
    assert move.status_code == 200, move.text
    assert move.json()["team"]["id"] == str(team.id)
    assert move.json()["owner"]["id"] == str(test_user_2.id)

    detach = client.patch(
        f"/api/admin/projects/{project.id}/team",
        headers=headers,
        json={"teamId": None},
    )
    assert detach.status_code == 200, detach.text
    assert detach.json()["team"] is None

    owner = client.patch(
        f"/api/admin/projects/{project.id}/owner",
        headers=headers,
        json={"ownerId": str(test_user.id)},
    )
    assert owner.status_code == 200, owner.text
    assert owner.json()["owner"]["id"] == str(test_user.id)

    listed = client.get("/api/admin/projects?q=Admin", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
