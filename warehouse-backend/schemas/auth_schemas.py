from datetime import datetime
from pydantic import BaseModel, EmailStr

from models.user_model import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    mobile: str
    role: UserRole
    warehouse_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LogoutResponse(BaseModel):
    message: str
