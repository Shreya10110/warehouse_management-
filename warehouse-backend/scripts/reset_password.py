"""Reset an existing WMS user's password through the configured database."""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import close_database, connect_database
from core.security import hash_password
from cruds.user_crud import find_user_by_email, update_user


async def main(email: str, password: str) -> None:
    await connect_database()
    try:
        user = await find_user_by_email(email)
        if not user:
            raise SystemExit(f"User not found: {email}")
        await update_user(user.id, {"password_hash": hash_password(password)})
        print(f"Password reset completed for {user.email}")
    finally:
        await close_database()


parser = argparse.ArgumentParser()
parser.add_argument("--email", required=True)
parser.add_argument("--password", required=True)

if __name__ == "__main__":
    args = parser.parse_args()
    asyncio.run(main(args.email, args.password))
