"""Read-only Owner/Admin account status check."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import close_mongo_connection, connect_to_mongo, get_database
from core.models.user_model import UserRole


async def run() -> None:
    await connect_to_mongo()
    try:
        owners = await get_database().users.find(
            {"role": UserRole.OWNER.value},
            {"email": 1, "role": 1, "is_active": 1, "approval_status": 1},
        ).to_list(length=20)
        print(f"Owner accounts: {len(owners)}")
        for owner in owners:
            print(
                f"- {owner.get('email')} | active={owner.get('is_active')} "
                f"| approval={owner.get('approval_status')}"
            )
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(run())
