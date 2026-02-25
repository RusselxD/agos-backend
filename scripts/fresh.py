import sys
import asyncio
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text
from alembic.config import Config
from alembic import command

async def drop_tables():
    """Drop all tables and enum types in public schema (does not require schema owner)"""
    print("🗑️  Dropping all tables and types...")
    drop_all_sql = text("""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            -- Drop tables first
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
            -- Drop enum types (e.g. notificationtype, responderstatus) - they persist after table drop
            FOR r IN (
                SELECT t.typname
                FROM pg_type t
                JOIN pg_namespace n ON t.typnamespace = n.oid
                WHERE n.nspname = 'public' AND t.typtype = 'e'
            ) LOOP
                EXECUTE 'DROP TYPE IF EXISTS public.' || quote_ident(r.typname) || ' CASCADE';
            END LOOP;
        END $$;
    """)
    async with engine.begin() as conn:
        await conn.execute(drop_all_sql)
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