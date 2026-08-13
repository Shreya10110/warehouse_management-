import asyncio

from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import core.database as database_module
from core.security import hash_password
from main import app
from models.user_model import User, UserRole
from models.warehouse_model import Warehouse


def login(client: TestClient, email: str, password: str = "StrongPass123") -> tuple[int, dict]:
    """Submit credentials and return status plus JSON response."""
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.status_code, response.json()


def signup(client: TestClient, email: str, role: str, warehouse_id: str) -> tuple[int, dict]:
    """Register a predictable manager or employee test applicant."""
    response = client.post("/api/v1/auth/signup", json={
        "first_name": role.title(), "last_name": "Applicant", "email": email,
        "mobile": "9999999999", "password": "StrongPass123", "role": role,
        "warehouse_id": warehouse_id,
    })
    return response.status_code, response.json()


def test_owner_and_manager_approval_chain_with_warehouse_isolation() -> None:
    """Require owner approval for managers and same-warehouse manager approval for employees."""
    mock_client = AsyncMongoMockClient()
    database_module.client = mock_client
    database_module.database = mock_client.approval_test
    owner = User(
        first_name="Whitfield", last_name="Owner", email="owner@whitfield.example.com", mobile="9999999999",
        password_hash=hash_password("StrongPass123"), role=UserRole.OWNER,
    )
    first = Warehouse(
        warehouse_code="WH-WFD-01", name="Whitfield Fulfillment", address_line_1="42 Industrial Layout",
        city="Bengaluru", state="Karnataka", postal_code="560066", contact_phone="9999999999",
        contact_email="ops@whitfield.example.com",
    )
    second = Warehouse(
        warehouse_code="WH-MYS-02", name="Mysuru Fulfillment", address_line_1="12 Logistics Road",
        city="Mysuru", state="Karnataka", postal_code="570001", contact_phone="8888888888",
        contact_email="ops@mysuru.example.com",
    )

    async def seed() -> None:
        """Seed the owner and two active signup warehouse choices."""
        await database_module.database.users.insert_one(owner.to_document())
        await database_module.database.warehouses.insert_many([first.to_document(), second.to_document()])

    asyncio.run(seed())
    client = TestClient(app, raise_server_exceptions=False)
    choices = client.get("/api/v1/auth/signup/warehouses")
    assert choices.status_code == 200
    assert {item["name"] for item in choices.json()} == {"Whitfield Fulfillment", "Mysuru Fulfillment"}

    status, manager_signup = signup(client, "manager1@whitfield.example.com", "MANAGER", first.id)
    assert status == 201, manager_signup
    assert manager_signup["approval_status"] == "PENDING_OWNER_APPROVAL"
    status, pending_login = login(client, "manager1@whitfield.example.com")
    assert status == 403
    assert pending_login["detail"]["code"] == "ACCOUNT_PENDING_APPROVAL"

    owner_status, owner_login = login(client, owner.email)
    assert owner_status == 200
    owner_headers = {"Authorization": f"Bearer {owner_login['access_token']}"}
    pending_managers = client.get("/api/v1/approvals/pending", headers=owner_headers).json()
    assert [item["email"] for item in pending_managers] == ["manager1@whitfield.example.com"]
    approved = client.post(f"/api/v1/approvals/{manager_signup['user_id']}/approve", headers=owner_headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["approval_status"] == "APPROVED"

    manager_status, manager_login = login(client, "manager1@whitfield.example.com")
    assert manager_status == 200
    manager_headers = {"Authorization": f"Bearer {manager_login['access_token']}"}
    status, additional_manager = signup(client, "manager3@whitfield.example.com", "MANAGER", first.id)
    assert status == 201
    assert client.post(f"/api/v1/approvals/{additional_manager['user_id']}/approve", headers=owner_headers).status_code == 200
    assert login(client, "manager3@whitfield.example.com")[0] == 200
    status, employee_signup = signup(client, "inbound@whitfield.example.com", "INBOUND", first.id)
    assert status == 201
    assert employee_signup["approval_status"] == "PENDING_MANAGER_APPROVAL"
    assert login(client, "inbound@whitfield.example.com")[0] == 403
    pending_employees = client.get("/api/v1/approvals/pending", headers=manager_headers).json()
    assert [item["email"] for item in pending_employees] == ["inbound@whitfield.example.com"]

    status, second_manager_signup = signup(client, "manager2@mysuru.example.com", "MANAGER", second.id)
    assert status == 201
    assert client.post(f"/api/v1/approvals/{second_manager_signup['user_id']}/approve", headers=owner_headers).status_code == 200
    _, second_manager_login = login(client, "manager2@mysuru.example.com")
    second_manager_headers = {"Authorization": f"Bearer {second_manager_login['access_token']}"}
    cross_warehouse = client.post(f"/api/v1/approvals/{employee_signup['user_id']}/approve", headers=second_manager_headers)
    assert cross_warehouse.status_code == 403

    employee_approved = client.post(f"/api/v1/approvals/{employee_signup['user_id']}/approve", headers=manager_headers)
    assert employee_approved.status_code == 200, employee_approved.text
    employee_status, employee_login = login(client, "inbound@whitfield.example.com")
    assert employee_status == 200
    assert employee_login["user"]["warehouse_id"] == first.id
    employee_headers = {"Authorization": f"Bearer {employee_login['access_token']}"}
    own_dashboard = client.get("/api/v1/dashboard/inbound", headers=employee_headers)
    assert own_dashboard.status_code == 200, own_dashboard.text
    assert own_dashboard.json()["warehouse"]["name"] == "Whitfield Fulfillment"
