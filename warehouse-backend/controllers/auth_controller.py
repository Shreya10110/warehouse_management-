from services import auth_service
from schemas.auth_schemas import LoginRequest, LoginResponse, LogoutResponse, UserResponse
from models.user_model import User


async def login(payload: LoginRequest) -> LoginResponse:
    return await auth_service.login(payload)


async def me(user: User) -> UserResponse:
    return auth_service.public_user(user)


async def logout() -> LogoutResponse:
    return LogoutResponse(message="Logged out. Remove the bearer token from the client.")
