from services import auth_service
from schemas.auth_schemas import LoginRequest, LoginResponse, LogoutResponse, UserResponse
from models.user_model import User


async def login(payload: LoginRequest) -> LoginResponse:
    """Authenticate credentials through the authorization service."""
    return await auth_service.login(payload)


async def me(user: User) -> UserResponse:
    """Return the current user's safe public profile."""
    return auth_service.public_user(user)


async def logout(token: str) -> LogoutResponse:
    """Revoke the bearer token and confirm logout to the client."""
    await auth_service.revoke_access_token(token)
    return LogoutResponse(message="Logged out. Remove the bearer token from the client.")
