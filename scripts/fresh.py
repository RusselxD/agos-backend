import sys
import asyncio
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import sqlalchemy
from app.core.database import engine
from sqlalchemy import text
from alembic.config import Config
from alembic import command

def _quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'

async def drop_tables():
    """Drop all tables and enum types in public schema."""
    print("🗑️  Dropping all tables and types...")

    # Fetch names first, then issue separate DROP statements.
    # This avoids one large statement that commonly hits statement_timeout on pooled connections.
    async with engine.connect() as conn:
        table_rows = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        tables = [row[0] for row in table_rows]

        enum_rows = await conn.execute(
            text(
                """
                SELECT t.typname
                FROM pg_type t
                JOIN pg_namespace n ON t.typnamespace = n.oid
                WHERE n.nspname = 'public' AND t.typtype = 'e'
                """
            )
        )
        enum_types = [row[0] for row in enum_rows]

    try:
        for table_name in tables:
            qualified_name = f"public.{_quote_ident(table_name)}"
            async with engine.begin() as conn:
                await conn.execute(text("SET LOCAL statement_timeout = 0"))
                await conn.execute(text(f"DROP TABLE IF EXISTS {qualified_name} CASCADE"))

        for type_name in enum_types:
            qualified_name = f"public.{_quote_ident(type_name)}"
            async with engine.begin() as conn:
                await conn.execute(text("SET LOCAL statement_timeout = 0"))
                await conn.execute(text(f"DROP TYPE IF EXISTS {qualified_name} CASCADE"))
    except sqlalchemy.exc.DBAPIError as exc:
        message = str(exc).lower()
        if "statement timeout" in message and ":6543/" in str(engine.url):
            raise RuntimeError(
                "Drop timed out on Supabase pooler (port 6543). "
                "Use the direct database URL on port 5432 for fresh/migration scripts."
            ) from exc
        raise

    print("✅ All tables and types dropped!")

async def main():
    await drop_tables()
    
    print("🗑️  Deleting old migrations...")
    versions_dir = Path("alembic/versions")
    for file in versions_dir.glob("*.py"):
        if file.name != "__init__.py":
            file.unlink()
    print("✅ Migrations deleted!")

    print("🔄 Creating new migration...")
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, message="initial migration", autogenerate=True)
    print("✅ Migration created!")

    print("🔄 Applying migration...")
    command.upgrade(alembic_cfg, "head")
    print("✅ Migration applied!")

    print("\n🎉 Fresh database ready!")

if __name__ == "__main__":
    asyncio.run(main())
