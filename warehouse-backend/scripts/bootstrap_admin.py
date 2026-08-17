"""Create the configured first Owner and verify its credentials."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.apis.schemas.auth_schemas import LoginRequest
from core.config import settings
from core.database import close_mongo_connection, connect_to_mongo
from core.services.auth_service import ensure_bootstrap_owner, login


async def run() -> None:
    if not settings.bootstrap_owner_password:
        raise RuntimeError("BOOTSTRAP_OWNER_PASSWORD is required")
    await connect_to_mongo()
    try:
        created = await ensure_bootstrap_owner()
        authenticated = await login(LoginRequest(
            email=settings.bootstrap_owner_email,
            password=settings.bootstrap_owner_password,
        ))
        action = "created" if created else "already existed"
        print(f"Admin {action} and login verified: {authenticated.user.email}")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(run())
