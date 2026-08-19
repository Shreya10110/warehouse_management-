"""Static contracts that keep Supabase aligned with the application domain."""
import json
from datetime import datetime, timezone
from pathlib import Path

from core.database.postgres import _compile_query, _serialize_value
from models.audit_log_model import AuditLog
from models.damage_report_model import DamageReport
from models.inbound_shipment_model import InboundShipment
from models.inventory_model import Inventory
from models.inventory_transaction_model import InventoryTransaction
from models.issue_request_model import IssueRequest
from models.order_model import Order
from models.package_model import Package
from models.product_model import Product
from models.seller_model import Seller
from models.user_model import User
from models.warehouse_model import Warehouse


def test_supabase_schema_contains_every_model_table_and_field() -> None:
    """Prevent API models from silently drifting away from SQL columns."""
    sql = (Path(__file__).parents[1] / "supabase_schema.sql").read_text(encoding="utf-8").lower()
    models = {
        "users": User,
        "warehouses": Warehouse,
        "products": Product,
        "sellers": Seller,
        "inbound_shipments": InboundShipment,
        "damage_reports": DamageReport,
        "inventory": Inventory,
        "inventory_transactions": InventoryTransaction,
        "orders": Order,
        "packages": Package,
        "issue_requests": IssueRequest,
        "audit_logs": AuditLog,
    }
    for table, model in models.items():
        assert f"create table if not exists {table}" in sql
        for field in model.model_fields:
            column = "id" if field == "id" else field
            assert column.lower() in sql, f"{table}.{column} is missing from Supabase schema"


def test_postgres_query_compiler_supports_application_filters() -> None:
    """Cover equality, identifiers, role lists, regex search, and JSON text search."""
    where, params = _compile_query({
        "_id": "abc",
        "role": {"$in": ["INBOUND", "OUTBOUND"]},
        "$or": [
            {"customer_name": {"$regex": "asha", "$options": "i"}},
            {"items.sku": {"$regex": "SKU-1", "$options": "i"}},
        ],
    })
    assert '"id" = $1' in where
    assert '"role" IN ($2, $3)' in where
    assert '"customer_name" ILIKE' in where
    assert '"items"::text ILIKE' in where
    assert params == ["abc", "INBOUND", "OUTBOUND", "asha", "SKU-1"]

    numeric_where, numeric_params = _compile_query({"quarantine_quantity": {"$gt": 0}})
    assert numeric_where == '"quarantine_quantity" > $1'
    assert numeric_params == [0]


def test_postgres_serializes_datetimes_nested_in_jsonb_documents() -> None:
    timestamp = datetime(2026, 8, 19, 12, 30, tzinfo=timezone.utc)
    serialized = _serialize_value({"status": "COMPLETED", "updated_at": timestamp})
    assert json.loads(serialized) == {
        "status": "COMPLETED",
        "updated_at": "2026-08-19T12:30:00+00:00",
    }
