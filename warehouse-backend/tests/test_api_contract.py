from main import app


def test_required_api_paths_are_registered() -> None:
    """Ensure the complete planned backend surface remains registered in OpenAPI."""
    paths = app.openapi()["paths"]
    required = {
        "/api/v1/auth/login", "/api/v1/auth/signup", "/api/v1/auth/signup/warehouses", "/api/v1/auth/me", "/api/v1/approvals/pending", "/api/v1/approvals/{user_id}/approve", "/api/v1/warehouses", "/api/v1/users",
        "/api/v1/products", "/api/v1/inventory", "/api/v1/inventory/adjust",
        "/api/v1/inbound/shipments", "/api/v1/inbound/receipts", "/api/v1/damage-reports", "/api/v1/orders",
        "/api/v1/orders/{order_id}/assign-warehouse", "/api/v1/orders/{order_id}/start-picking",
        "/api/v1/orders/{order_id}/pack", "/api/v1/packages/{package_id}/generate-label",
        "/api/v1/packages/{package_id}/ship", "/api/v1/audit-logs", "/api/v1/dashboard/admin",
        "/api/v1/dashboard/manager", "/api/v1/dashboard/inbound", "/api/v1/dashboard/outbound",
    }
    assert required <= set(paths)
