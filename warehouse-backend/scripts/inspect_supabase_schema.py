"""Print legacy required columns that are not supplied by current models."""
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.database.postgres import get_postgres_dsn


async def main() -> None:
    connection = await asyncpg.connect(get_postgres_dsn())
    try:
        rows = await connection.fetch(
            "SELECT table_name, column_name, is_nullable, column_default "
            "FROM information_schema.columns WHERE table_schema='public' "
            "ORDER BY table_name, ordinal_position"
        )
        for row in rows:
            if row["is_nullable"] == "NO" and row["column_default"] is None:
                print(f"{row['table_name']}.{row['column_name']}: required, no default")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
