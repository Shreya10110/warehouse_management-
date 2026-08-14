from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from models.user_model import ApprovalStatus, UserRole


class LoginRequest(BaseModel):
    """Email and password credentials for an approved account."""
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    """Public manager or employee registration for a selected active warehouse."""
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    mobile: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    warehouse_id: str


class SignupResponse(BaseModel):
    """Safe registration result explaining the next approval step."""
    user_id: str
    email: EmailStr
    role: UserRole
    warehouse_id: str
    approval_status: ApprovalStatus
    message: str


class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    mobile: str
    role: UserRole
    warehouse_id: str | None
    is_active: bool
    approval_status: ApprovalStatus
    approved_by: str | None
    approved_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LogoutResponse(BaseModel):
    """Confirmation returned after token revocation."""
    message: str
