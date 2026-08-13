from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.exceptions import AppError
from core.security import decode_access_token
from cruds.user_crud import find_user_by_id
from core.database import get_database
from models.user_model import User, UserRole

bearer = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    """Resolve the active user represented by a bearer JWT."""
    if not credentials:
        raise AppError(401, "UNAUTHORIZED", "Authentication is required.")
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise AppError(401, "UNAUTHORIZED", str(exc)) from exc
    if await get_database().revoked_tokens.find_one({"jti": claims.get("jti")}):
        raise AppError(401, "UNAUTHORIZED", "This access token has been logged out.")
    user = await find_user_by_id(str(claims.get("user_id", "")))
    if not user or not user.is_active:
        raise AppError(401, "UNAUTHORIZED", "User is unavailable or inactive.")
    return user


def require_roles(*roles: UserRole):
    """Create a dependency that restricts access to the supplied roles."""
    async def dependency(user: User = Depends(get_current_user)) -> User:
        """Return the user when their role is allowed, otherwise reject access."""
        if user.role not in roles:
            raise AppError(403, "FORBIDDEN", "You do not have permission for this operation.")
        return user
    return dependency


require_owner = require_roles(UserRole.OWNER)
require_manager = require_roles(UserRole.MANAGER)
require_inbound = require_roles(UserRole.INBOUND)
require_outbound = require_roles(UserRole.OUTBOUND)
require_warehouse_staff = require_roles(UserRole.MANAGER, UserRole.INBOUND, UserRole.OUTBOUND)
require_owner_or_manager = require_roles(UserRole.OWNER, UserRole.MANAGER)
