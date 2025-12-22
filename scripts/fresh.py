import sys
import asyncio
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text
from alembic.config import Config
from alembic import command

async def drop_tables():
    """Drop all tables using async engine"""
    from app.models.base import Base
    
    print("🗑️  Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✅ Tables dropped!")

    print("🗑️  Dropping alembic_version table...")
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version;"))
    print("✅ Alembic version table dropped!")

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