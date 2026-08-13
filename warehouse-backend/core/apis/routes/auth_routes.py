from fastapi import APIRouter, Depends, status

from controllers import auth_controller
from dependencies.auth import bearer, get_current_user
from fastapi.security import HTTPAuthorizationCredentials
from models.user_model import User
from schemas.auth_schemas import LoginRequest, LoginResponse, LogoutResponse, SignupRequest, SignupResponse, UserResponse
from cruds.base_crud import CRUDRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])
warehouse_repo = CRUDRepository("warehouses")


@router.get("/signup/warehouses")
async def signup_warehouses():
    """List safe active warehouse choices for the public registration form."""
    warehouses = await warehouse_repo.list({"is_active": True}, limit=200)
    return [
        {"id": item["id"], "warehouse_code": item["warehouse_code"], "name": item["name"], "city": item["city"], "state": item["state"]}
        for item in warehouses
    ]


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest) -> SignupResponse:
    """Create a pending manager, inbound, or outbound registration."""
    return await auth_controller.signup(payload)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    """Authenticate an email and password and return a bearer session."""
    return await auth_controller.login(payload)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the profile represented by the current bearer token."""
    return await auth_controller.me(user)


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer), _: User = Depends(get_current_user)) -> LogoutResponse:
    """Revoke the authenticated bearer token and confirm logout."""
    return await auth_controller.logout(credentials.credentials)
