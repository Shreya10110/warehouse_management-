"""Execute the Supabase SQL schema against the configured database."""

import argparse
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse
import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings
from core.database.postgres import get_postgres_dsn


async def run_migration(custom_dsn: str | None = None) -> None:
    """Read supabase_schema.sql and execute it against PostgreSQL."""
    dsn = custom_dsn or get_postgres_dsn()
    if not dsn:
        print("ERROR: No PostgreSQL / Supabase connection DSN found.")
        print("Please set SUPABASE_DB_PASSWORD in .env or pass --dsn / --password.")
        sys.exit(1)

    schema_file = Path(__file__).resolve().parents[1] / "supabase_schema.sql"
    if not schema_file.exists():
        print(f"ERROR: Schema file not found at {schema_file}")
        sys.exit(1)

    sql_content = schema_file.read_text(encoding="utf-8")
    print(f"Connecting to database...")

    try:
        conn = await asyncpg.connect(dsn=dsn, timeout=15)
        print("Connected successfully! Executing schema script...")
        await conn.execute(sql_content)
        print("SUCCESS: Supabase tables, compatibility repairs, and indexes applied!")
        await conn.close()
    except Exception as exc:
        print(f"FAILED to execute schema: {exc}")
        sys.exit(1)


parser = argparse.ArgumentParser(description="Apply Supabase schema migration")
parser.add_argument("--password", help="Supabase database password")
parser.add_argument("--dsn", help="Full PostgreSQL connection DSN")

if __name__ == "__main__":
    args = parser.parse_args()
    override_dsn = None
    if args.password:
        project_ref = urlparse(settings.supabase_url).hostname.split(".")[0]
        override_dsn = f"postgresql://postgres:{args.password}@db.{project_ref}.supabase.co:5432/postgres"
    elif args.dsn:
        override_dsn = args.dsn

    asyncio.run(run_migration(override_dsn))
