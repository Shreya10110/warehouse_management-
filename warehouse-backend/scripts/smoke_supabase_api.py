"""Live Supabase API smoke test with fully cleaned temporary records."""
import asyncio
import sys
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
email = f"supabase-smoke-{suffix}@example.com"
password = f"Smoke-{uuid4().hex}!"
seller_code = f"SMOKE-{suffix.upper()}"
seller_id = None


async def seed_owner() -> None:
    connection = await asyncpg.connect(get_postgres_dsn())
    try:
        now = datetime.now(timezone.utc)
        await connection.execute(
            "INSERT INTO users (id, first_name, last_name, email, mobile, password_hash, role, "
            "is_active, approval_status, created_at, updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$10)",
            user_id, "Supabase", "Smoke", email, "0000000000", hash_password(password),
            "OWNER", True, "APPROVED", now,
        )
    finally:
        await connection.close()


async def cleanup() -> None:
    connection = await asyncpg.connect(get_postgres_dsn())
    try:
        if seller_id:
            await connection.execute("DELETE FROM audit_logs WHERE entity_id = $1", seller_id)
            await connection.execute("DELETE FROM sellers WHERE id = $1", seller_id)
        await connection.execute("DELETE FROM users WHERE id = $1", user_id)
    finally:
        await connection.close()


asyncio.run(seed_owner())
try:
    with TestClient(app, raise_server_exceptions=False) as client:
        checks = []
        checks.append(("GET /health", client.get("/health")))
        checks.append(("GET /auth/signup/warehouses", client.get("/api/v1/auth/signup/warehouses")))
        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        checks.append(("POST /auth/login", login))
        if login.status_code == 200:
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            checks.append(("GET /auth/me", client.get("/api/v1/auth/me", headers=headers)))
            checks.append(("GET /sellers", client.get("/api/v1/sellers", headers=headers)))
            created = client.post(
                "/api/v1/sellers", headers=headers,
                json={"seller_code": seller_code, "name": "Temporary Supabase Smoke Seller"},
            )
            checks.append(("POST /sellers", created))
            if created.status_code == 200:
                seller_id = created.json()["id"]
            checks.append(("GET /dashboard/admin", client.get("/api/v1/dashboard/admin", headers=headers)))
        for label, response in checks:
            print(f"{label} -> {response.status_code}")
        failed = [(label, response.json()) for label, response in checks if response.status_code != 200]
        if failed:
            raise RuntimeError(f"Live API checks failed: {failed}")
        print("Supabase API smoke test: successful")
finally:
    asyncio.run(cleanup())
    print("Temporary smoke-test records: removed")
