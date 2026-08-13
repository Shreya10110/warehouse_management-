from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.exceptions import AppError
from core.security import decode_access_token
from cruds.user_crud import find_user_by_id
from models.user_model import User

bearer = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if not credentials:
        raise AppError(401, "UNAUTHORIZED", "Authentication is required.")
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise AppError(401, "UNAUTHORIZED", str(exc)) from exc
    user = await find_user_by_id(str(claims.get("user_id", "")))
    if not user or not user.is_active:
        raise AppError(401, "UNAUTHORIZED", "User is unavailable or inactive.")
    return user
