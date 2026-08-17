import asyncio

from mongomock_motor import AsyncMongoMockClient

import core.database as database_module
from core.config import settings
from core.services.auth_service import ensure_bootstrap_owner, login
from schemas.auth_schemas import LoginRequest


def test_bootstrap_owner_is_created_once_and_can_login(monkeypatch) -> None:
    """Bootstrap credentials create one approved Owner and authenticate."""
    mock_client = AsyncMongoMockClient()
    database_module.client = mock_client
    database_module.database = mock_client.warehouse_bootstrap_test
    monkeypatch.setattr(settings, "bootstrap_owner_email", "admin@whitfield.example.com")
    monkeypatch.setattr(settings, "bootstrap_owner_password", "SecureAdminPass123")
    monkeypatch.setattr(settings, "bootstrap_owner_first_name", "Warehouse")
    monkeypatch.setattr(settings, "bootstrap_owner_last_name", "Owner")
    monkeypatch.setattr(settings, "bootstrap_owner_mobile", "9999999999")

    created = asyncio.run(ensure_bootstrap_owner())
    repeated = asyncio.run(ensure_bootstrap_owner())
    authenticated = asyncio.run(login(LoginRequest(
        email="admin@whitfield.example.com", password="SecureAdminPass123"
    )))

    assert created is not None
    assert created.role.value == "OWNER"
    assert created.is_active is True
    assert repeated is None
    assert authenticated.user.email == "admin@whitfield.example.com"
    assert asyncio.run(database_module.database.users.count_documents({"role": "OWNER"})) == 1
