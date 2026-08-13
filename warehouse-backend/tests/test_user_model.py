import pytest
from pydantic import ValidationError

from models.user_model import User, UserRole


BASE = dict(first_name="A", last_name="User", email="A@EXAMPLE.COM", mobile="1234567890", password_hash="hash")


def test_owner_has_no_warehouse() -> None:
    user = User(**BASE, role=UserRole.OWNER)
    assert user.warehouse_id is None
    assert user.email == "a@example.com"


def test_employee_requires_warehouse() -> None:
    with pytest.raises(ValidationError):
        User(**BASE, role=UserRole.INBOUND)
