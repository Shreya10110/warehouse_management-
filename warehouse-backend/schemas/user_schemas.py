from pydantic import BaseModel, EmailStr, Field, model_validator

from models.user_model import UserRole


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    mobile: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    warehouse_id: str | None = None

    @model_validator(mode="after")
    def validate_role_assignment(self) -> "UserCreate":
        if self.role == UserRole.OWNER and self.warehouse_id is not None:
            raise ValueError("OWNER must not have a warehouse_id")
        if self.role != UserRole.OWNER and not self.warehouse_id:
            raise ValueError(f"{self.role} must have a warehouse_id")
        return self
