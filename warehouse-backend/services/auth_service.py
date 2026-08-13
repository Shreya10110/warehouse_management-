from pymongo.errors import DuplicateKeyError

from core.exceptions import AppError
from core.security import create_access_token, decode_access_token, hash_password, verify_password
from core.database import get_database
from datetime import datetime, timezone
from cruds.user_crud import create_user, find_user_by_email, update_last_login
from models.user_model import User
from schemas.auth_schemas import LoginRequest, LoginResponse, UserResponse
from schemas.user_schemas import UserCreate


def public_user(user: User) -> UserResponse:
    """Serialize a user without exposing the password hash."""
    return UserResponse.model_validate(user.model_dump(by_alias=False))


async def register_user(payload: UserCreate) -> UserResponse:
    """Hash credentials and persist a validated unique user."""
    user = User(**payload.model_dump(exclude={"password"}), password_hash=hash_password(payload.password))
    try:
        await create_user(user)
    except DuplicateKeyError as exc:
        raise AppError(409, "DUPLICATE_EMAIL", "A user with this email already exists.") from exc
    return public_user(user)


async def login(payload: LoginRequest) -> LoginResponse:
    """Authenticate an active user and issue role and warehouse JWT claims."""
    user = await find_user_by_email(str(payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
    if not user.is_active:
        raise AppError(403, "USER_INACTIVE", "This account is inactive.")
    user.last_login = await update_last_login(user.id)
    token = create_access_token({"user_id": user.id, "role": user.role.value, "warehouse_id": user.warehouse_id})
    return LoginResponse(access_token=token, user=public_user(user))


async def revoke_access_token(token: str) -> None:
    """Persist a JWT identifier until expiry so logout immediately revokes it."""
    claims = decode_access_token(token)
    expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    await get_database().revoked_tokens.update_one(
        {"jti": claims["jti"]}, {"$set": {"jti": claims["jti"], "expires_at": expires_at}}, upsert=True
    )
