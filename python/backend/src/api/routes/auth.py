import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase

from config.settings import get_settings
from db.database import get_async_session, get_user_db
from domain.api_tokens.error import (
    ApiTokenExpiredError,
    ApiTokenInvalidError,
    ApiTokenRevokedError,
)
from domain.api_tokens.service import ApiTokenService
from domain.team.users.dto import UserCreate, UserRead, UserUpdate
from models import User

SECRET = get_settings().jwt_secret


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} ({user.email}) has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has requested password reset. Token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Token: {token}")


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


API_PREFIX = get_settings().api_prefix
bearer_transport = BearerTransport(tokenUrl=f"{API_PREFIX}/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600 * 24 * 7)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_active_user_optional = fastapi_users.current_user(active=True, optional=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_by_api_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session=Depends(get_async_session),
):
    if credentials is None or not credentials.credentials:
        return None
    service = ApiTokenService(session)
    try:
        token = await service.validate_token(credentials.credentials)
        await service.mark_used(token)
        request.state.api_token_scopes = token.scopes or []
        request.state.api_token_id = token.id
        return token.user
    except (ApiTokenInvalidError, ApiTokenRevokedError, ApiTokenExpiredError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def get_current_user_dual(
    request: Request,
    jwt_user: User | None = Depends(current_active_user_optional),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session=Depends(get_async_session),
) -> User:
    token_value = credentials.credentials if credentials else None
    if token_value and token_value.startswith("pat_"):
        user = await get_current_user_by_api_token(
            request=request, credentials=credentials, session=session
        )
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid API token")
        return user
    if jwt_user is not None:
        return jwt_user
    if token_value:
        user = await get_current_user_by_api_token(
            request=request, credentials=credentials, session=session
        )
        if user is not None:
            return user
    raise HTTPException(status_code=401, detail="Not authenticated")


def require_api_token_scopes(required: str | list[str]):
    required_list = [required] if isinstance(required, str) else list(required)

    async def _dependency(request: Request) -> None:
        scopes = getattr(request.state, "api_token_scopes", None)
        if scopes is None:
            return
        missing = [scope for scope in required_list if scope not in scopes]
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"API token missing scopes: {', '.join(missing)}",
            )

    return _dependency


router = APIRouter()

router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)
router.include_router(
    fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"]
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@router.get("/users/me/profile", response_model=UserRead, tags=["users"])
async def get_my_profile(user: User = Depends(get_current_user_dual)) -> User:
    return user
