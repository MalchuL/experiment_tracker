"""HTTP routes under ``/hypotheses``: CRUD and listing for project hypotheses."""

from uuid import UUID

from api.routes.service_dependencies import get_hypothesis_service
from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.auth import get_current_user_dual, require_api_token_scopes
from lib.pagination import MAX_LIST_PAGE_SIZE, ListOptions
from models import User
from domain.rbac.permissions import ProjectActions

from .dto import (
    HypothesisCreateDTO,
    HypothesisDTO,
    HypothesisListResponseDTO,
    HypothesisUpdateDTO,
)
from .error import HypothesisNotAccessibleError, HypothesisNotFoundError
from .service import HypothesisService

router = APIRouter(prefix="/hypotheses", tags=["hypotheses"])


def _raise_hypothesis_http_error(error: Exception) -> None:
    """Map hypothesis domain errors to HTTP status codes.

    Args:
        error: Exception raised by ``HypothesisService``.

    Raises:
        HTTPException: ``403`` for access denial, ``404`` for missing hypotheses,
            and ``400`` for validation or persistence errors.
    """
    if isinstance(error, HypothesisNotAccessibleError):
        raise HTTPException(status_code=403, detail=str(error))
    if isinstance(error, HypothesisNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    raise HTTPException(status_code=400, detail=str(error))


@router.get("/recent", response_model=HypothesisListResponseDTO)
async def get_recent_hypotheses(
    projectId: UUID,
    limit: int = Query(default=10, ge=1, le=MAX_LIST_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_HYPOTHESIS)),
    hypothesis_service: HypothesisService = Depends(get_hypothesis_service),
):
    """List recent hypotheses for a project.

    Args:
        projectId: Project identifier supplied as a query parameter.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.
        user: Authenticated user requesting the list.
        _: API-token scope guard requiring hypothesis view access.
        hypothesis_service: Hypothesis application service dependency.

    Returns:
        HypothesisListResponseDTO: Paginated project hypotheses.

    Raises:
        ProjectNotAccessibleError: Propagated by the service when the project is not
            visible to the user.
    """
    return await hypothesis_service.get_hypotheses_by_project(
        user,
        projectId,
        ListOptions(limit=limit, offset=offset),
    )


@router.get("/{hypothesis_id}", response_model=HypothesisDTO)
async def get_hypothesis(
    hypothesis_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.VIEW_HYPOTHESIS)),
    hypothesis_service: HypothesisService = Depends(get_hypothesis_service),
):
    """Return one hypothesis visible to the current user.

    Args:
        hypothesis_id: Identifier of the hypothesis to fetch.
        user: Authenticated user requesting the hypothesis.
        _: API-token scope guard requiring hypothesis view access.
        hypothesis_service: Hypothesis application service dependency.

    Returns:
        HypothesisDTO: Full hypothesis payload.

    Raises:
        HTTPException: ``403`` when access is denied, ``404`` when not found, or
            ``400`` for other service errors.
    """
    try:
        return await hypothesis_service.get_hypothesis_if_accessible(
            user, hypothesis_id
        )
    except Exception as exc:  # noqa: BLE001
        _raise_hypothesis_http_error(exc)


@router.post("", response_model=HypothesisDTO)
async def create_hypothesis(
    data: HypothesisCreateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.CREATE_HYPOTHESIS)),
    hypothesis_service: HypothesisService = Depends(get_hypothesis_service),
):
    """Create a hypothesis in a project.

    Args:
        data: Create DTO with project id and hypothesis fields.
        user: Authenticated user creating the hypothesis.
        _: API-token scope guard requiring hypothesis creation access.
        hypothesis_service: Hypothesis application service dependency.

    Returns:
        HypothesisDTO: Newly created hypothesis.

    Raises:
        HTTPException: ``403`` when the target project is inaccessible, or ``400`` for
            validation and repository errors.
    """
    try:
        return await hypothesis_service.create_hypothesis(user, data)
    except Exception as exc:  # noqa: BLE001
        _raise_hypothesis_http_error(exc)


@router.patch("/{hypothesis_id}", response_model=HypothesisDTO)
async def update_hypothesis(
    hypothesis_id: UUID,
    data: HypothesisUpdateDTO,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.EDIT_HYPOTHESIS)),
    hypothesis_service: HypothesisService = Depends(get_hypothesis_service),
):
    """Patch an existing hypothesis.

    Args:
        hypothesis_id: Identifier of the hypothesis to update.
        data: Update DTO containing editable fields.
        user: Authenticated user editing the hypothesis.
        _: API-token scope guard requiring hypothesis edit access.
        hypothesis_service: Hypothesis application service dependency.

    Returns:
        HypothesisDTO: Updated hypothesis.

    Raises:
        HTTPException: ``403`` for permission failures, ``404`` for missing
            hypotheses, and ``400`` for other service errors.
    """
    try:
        return await hypothesis_service.update_hypothesis(user, hypothesis_id, data)
    except Exception as exc:  # noqa: BLE001
        _raise_hypothesis_http_error(exc)


@router.delete("/{hypothesis_id}")
async def delete_hypothesis(
    hypothesis_id: UUID,
    user: User = Depends(get_current_user_dual),
    _: None = Depends(require_api_token_scopes(ProjectActions.DELETE_HYPOTHESIS)),
    hypothesis_service: HypothesisService = Depends(get_hypothesis_service),
):
    """Delete a hypothesis.

    Args:
        hypothesis_id: Identifier of the hypothesis to delete.
        user: Authenticated user deleting the hypothesis.
        _: API-token scope guard requiring hypothesis delete access.
        hypothesis_service: Hypothesis application service dependency.

    Returns:
        dict[str, bool]: ``{"success": True}`` after deletion.

    Raises:
        HTTPException: ``403`` for permission failures, ``404`` when the hypothesis is
            missing, and ``400`` for other service errors.
    """
    try:
        success = await hypothesis_service.delete_hypothesis(user, hypothesis_id)
    except Exception as exc:  # noqa: BLE001
        _raise_hypothesis_http_error(exc)
    if not success:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return {"success": True}
