from pymongo.errors import DuplicateKeyError

from core.exceptions import AppError
from core.security import create_access_token, hash_password, verify_password
from cruds.user_crud import create_user, find_user_by_email, update_last_login
from models.user_model import User
from schemas.auth_schemas import LoginRequest, LoginResponse, UserResponse
from schemas.user_schemas import UserCreate


def public_user(user: User) -> UserResponse:
    return UserResponse.model_validate(user.model_dump(by_alias=False))


async def register_user(payload: UserCreate) -> UserResponse:
    user = User(**payload.model_dump(exclude={"password"}), password_hash=hash_password(payload.password))
    try:
        await create_user(user)
    except DuplicateKeyError as exc:
        raise AppError(409, "DUPLICATE_EMAIL", "A user with this email already exists.") from exc
    return public_user(user)


async def login(payload: LoginRequest) -> LoginResponse:
    user = await find_user_by_email(str(payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
    if not user.is_active:
        raise AppError(403, "USER_INACTIVE", "This account is inactive.")
    user.last_login = await update_last_login(user.id)
    token = create_access_token({"user_id": user.id, "role": user.role.value, "warehouse_id": user.warehouse_id})
    return LoginResponse(access_token=token, user=public_user(user))
