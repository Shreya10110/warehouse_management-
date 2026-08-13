import argparse
import asyncio

from core.database import close_mongo_connection, connect_to_mongo
from models.user_model import UserRole
from schemas.user_schemas import UserCreate
from services.auth_service import register_user


async def run(args: argparse.Namespace) -> None:
    await connect_to_mongo()
    try:
        user = await register_user(UserCreate(**vars(args), role=UserRole(args.role)))
        print(f"Created {user.role} user {user.email} ({user.id})")
    finally:
        await close_mongo_connection()


parser = argparse.ArgumentParser(description="Create a WMS user")
parser.add_argument("--first-name", required=True)
parser.add_argument("--last-name", required=True)
parser.add_argument("--email", required=True)
parser.add_argument("--mobile", required=True)
parser.add_argument("--password", required=True)
parser.add_argument("--role", choices=[role.value for role in UserRole], required=True)
parser.add_argument("--warehouse-id")

if __name__ == "__main__":
    asyncio.run(run(parser.parse_args()))
