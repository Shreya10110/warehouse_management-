from fastapi import APIRouter, Depends, status

from controllers import auth_controller
from dependencies.auth import get_current_user
from models.user_model import User
from schemas.auth_schemas import LoginRequest, LoginResponse, LogoutResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    return await auth_controller.login(payload)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return await auth_controller.me(user)


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(_: User = Depends(get_current_user)) -> LogoutResponse:
    return await auth_controller.logout()
