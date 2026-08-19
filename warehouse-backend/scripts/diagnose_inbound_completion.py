"""Reproduce Supabase inbound completion and fully restore temporary effects."""
import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database.postgres import get_postgres_dsn
from core.security import hash_password
from fastapi.testclient import TestClient
from main import app

suffix = uuid4().hex[:10]
user_id = uuid4().hex
shipment_id = uuid4().hex
email = f"inbound-diagnostic-{suffix}@example.com"
password = f"Diagnostic-{uuid4().hex}!"
tracking = f"DIAG-{suffix.upper()}"
snapshot = None
warehouse_id = None
sku = None


async def seed() -> None:
    global snapshot, warehouse_id, sku
    connection = await asyncpg.connect(get_postgres_dsn())
    try:
        source = await connection.fetchrow(
            "SELECT warehouse_id, expected_items FROM inbound_shipments WHERE status='RECEIVING' LIMIT 1"
        )
        warehouse_id = source["warehouse_id"]
        items = json.loads(source["expected_items"]) if isinstance(source["expected_items"], str) else source["expected_items"]
        sku = items[0]["sku"]
        snapshot = await connection.fetchrow(
            "SELECT * FROM inventory WHERE warehouse_id=$1 AND sku=$2", warehouse_id, sku
        )
        now = datetime.now(timezone.utc)
        await connection.execute(
            "INSERT INTO users (id,first_name,last_name,email,mobile,password_hash,role,warehouse_id,is_active,approval_status,created_at,updated_at) "
            "VALUES ($1,$2,$3,$4,$5,$6,'INBOUND',$7,TRUE,'APPROVED',$8,$8)",
            user_id, "Inbound", "Diagnostic", email, "0000000000", hash_password(password), warehouse_id, now,
        )
        await connection.execute(
            "INSERT INTO inbound_shipments (id,shipment_id,warehouse_id,source_type,tracking_number,supplier_name,status,expected_items,received_items,created_by,created_at,updated_at) "
            "VALUES ($1,$2,$3,'CARRIER',$4,'Diagnostic Supplier','EXPECTED',$5::jsonb,'[]'::jsonb,$6,$7,$7)",
            shipment_id, f"IN-DIAG-{suffix.upper()}", warehouse_id, tracking,
            json.dumps([{"sku": sku, "expected_quantity": 1}]), user_id, now,
        )
    finally:
        await connection.close()


async def cleanup() -> None:
    connection = await asyncpg.connect(get_postgres_dsn())
    try:
        await connection.execute("DELETE FROM audit_logs WHERE user_id=$1", user_id)
        await connection.execute("DELETE FROM inventory_transactions WHERE performed_by=$1", user_id)
        await connection.execute("DELETE FROM damage_reports WHERE reported_by=$1", user_id)
        await connection.execute("DELETE FROM inbound_shipments WHERE id=$1", shipment_id)
        if snapshot:
            await connection.execute(
                "UPDATE inventory SET on_hand_quantity=$1,reserved_quantity=$2,damaged_quantity=$3,quarantine_quantity=$4,updated_at=$5 WHERE id=$6",
                snapshot["on_hand_quantity"], snapshot["reserved_quantity"], snapshot["damaged_quantity"],
                snapshot["quarantine_quantity"], snapshot["updated_at"], snapshot["id"],
            )
        else:
            await connection.execute("DELETE FROM inventory WHERE warehouse_id=$1 AND sku=$2", warehouse_id, sku)
        await connection.execute("DELETE FROM users WHERE id=$1", user_id)
    finally:
        await connection.close()


logging.disable(logging.CRITICAL)
asyncio.run(seed())
try:
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            lookup = client.post(
                "/api/v1/inbound/shipments/lookup", headers=headers,
                json={"source_type": "CARRIER", "tracking_number": tracking},
            )
            print(f"Diagnostic lookup: {lookup.status_code}")
            completed = client.post(
                f"/api/v1/inbound/shipments/{shipment_id}/complete", headers=headers,
                json={"items": [{"sku": sku, "received_quantity": 1, "damaged_quantity": 1}]},
            )
            print(f"Diagnostic completion: {completed.status_code}")
            print(completed.json())
    except Exception as exc:
        print(f"Diagnostic exception: {type(exc).__name__}: {exc}")
        frames = traceback.extract_tb(exc.__traceback__)[-8:]
        for frame in frames:
            print(f"  {frame.filename}:{frame.lineno} in {frame.name}: {frame.line}")
finally:
    asyncio.run(cleanup())
    print("Diagnostic records and inventory effects: restored")
