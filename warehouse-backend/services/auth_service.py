from pymongo.errors import DuplicateKeyError

from core.exceptions import AppError
from core.security import create_access_token, decode_access_token, hash_password, verify_password
from core.database import get_database
from datetime import datetime, timezone
from cruds.user_crud import create_user, find_user_by_email, update_last_login
from models.user_model import ApprovalStatus, User, UserRole
from schemas.auth_schemas import LoginRequest, LoginResponse, SignupRequest, SignupResponse, UserResponse
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
    if user.approval_status in (ApprovalStatus.PENDING_OWNER_APPROVAL, ApprovalStatus.PENDING_MANAGER_APPROVAL):
        approver = "the Whitfield Fulfillment owner" if user.role == UserRole.MANAGER else "your warehouse manager"
        raise AppError(403, "ACCOUNT_PENDING_APPROVAL", f"Your account is waiting for approval from {approver}.")
    if user.approval_status == ApprovalStatus.REJECTED:
        message = "Your registration was not approved."
        if user.rejection_reason:
            message = f"{message} Reason: {user.rejection_reason}"
        raise AppError(403, "ACCOUNT_REJECTED", message)
    if not user.is_active:
        raise AppError(403, "USER_INACTIVE", "This account is inactive.")
    user.last_login = await update_last_login(user.id)
    token = create_access_token({"user_id": user.id, "role": user.role.value, "warehouse_id": user.warehouse_id})
    return LoginResponse(access_token=token, user=public_user(user))


async def signup(payload: SignupRequest) -> SignupResponse:
    """Register a manager or employee in a pending warehouse approval state."""
    if payload.role == UserRole.OWNER:
        raise AppError(400, "INVALID_ROLE", "Owner accounts cannot be created through public signup.")
    if await find_user_by_email(str(payload.email)):
        raise AppError(409, "DUPLICATE_EMAIL", "An account with this email already exists.")
    from cruds.base_crud import CRUDRepository
    warehouse = await CRUDRepository("warehouses").get(payload.warehouse_id)
    if not warehouse or not warehouse.get("is_active"):
        raise AppError(404, "WAREHOUSE_NOT_FOUND", "Select an active verified warehouse.")
    approval_status = ApprovalStatus.PENDING_OWNER_APPROVAL if payload.role == UserRole.MANAGER else ApprovalStatus.PENDING_MANAGER_APPROVAL
    user = User(
        **payload.model_dump(exclude={"password"}), password_hash=hash_password(payload.password),
        is_active=False, approval_status=approval_status,
    )
    try:
        await create_user(user)
    except DuplicateKeyError as exc:
        raise AppError(409, "DUPLICATE_EMAIL", "An account with this email already exists.") from exc
    approver = "the Whitfield Fulfillment owner" if payload.role == UserRole.MANAGER else "the manager of your selected warehouse"
    return SignupResponse(
        user_id=user.id, email=user.email, role=user.role, warehouse_id=user.warehouse_id,
        approval_status=user.approval_status, message=f"Registration received. Your account now needs approval from {approver}.",
    )


async def revoke_access_token(token: str) -> None:
    """Persist a JWT identifier until expiry so logout immediately revokes it."""
    claims = decode_access_token(token)
    expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    await get_database().revoked_tokens.update_one(
        {"jti": claims["jti"]}, {"$set": {"jti": claims["jti"], "expires_at": expires_at}}, upsert=True
    )
