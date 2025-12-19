import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import Base, engine
from sqlalchemy import text
from alembic.config import Config
from alembic import command

print("🗑️  Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("✅ Tables dropped!")

print("🗑️  Dropping alembic_version table...")
with engine.connect() as connection:
    connection.execute(text("DROP TABLE IF EXISTS alembic_version;"))
    connection.commit()
print("✅ Alembic version table dropped!")

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