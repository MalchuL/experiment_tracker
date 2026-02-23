from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from domain.objects.error import ObjectsNotAccessibleError
from domain.objects.service import ObjectsService


@pytest.mark.asyncio
async def test_log_object_requires_permission() -> None:
    project_id = uuid4()
    experiment_id = uuid4()
    client = AsyncMock()
    permission_checker = AsyncMock()
    permission_checker.can_log_scalar.return_value = False
    experiment_repository = AsyncMock()
    experiment_repository.get_by_id.return_value = SimpleNamespace(project_id=project_id)
    service = ObjectsService(client, permission_checker, experiment_repository)

    with pytest.raises(ObjectsNotAccessibleError):
        await service.log_object(
            user=SimpleNamespace(id=uuid4()),
            experiment_id=experiment_id,
            payload={"name": "predictions"},
        )


@pytest.mark.asyncio
async def test_get_objects_forwards_to_client() -> None:
    project_id = uuid4()
    client = AsyncMock()
    client.get_objects.return_value = {"data": []}
    permission_checker = AsyncMock()
    permission_checker.can_view_scalar.return_value = True
    experiment_repository = AsyncMock()
    experiment_repository.get_experiments_by_ids.return_value = []
    service = ObjectsService(client, permission_checker, experiment_repository)

    result = await service.get_objects(
        user=SimpleNamespace(id=uuid4()),
        project_id=project_id,
        experiment_ids=None,
        object_types=["image"],
        names=["predictions"],
    )

    assert result == {"data": []}
    client.get_objects.assert_awaited_once()
