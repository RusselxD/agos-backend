#!/usr/bin/env bash
#
# Step 2 of the DB reset: build a fresh database from scratch.
#   1. Creates/ensures the FULL schema (all 20 tables) via Alembic.
#   2. TRUNCATEs the 17 preserved tables (clears any base-seed rows that the
#      app's start.sh -> seed_db.py may have already inserted).
#   3. Loads the preserved data dumped by dump_preserved.sh.
#
# The wiped tables (sensor_readings, model_readings, weather, daily_summaries)
# end up empty - regenerate them afterwards with scripts/seed_dummy_readings.py.
#
# Safe to run whether the new DB is empty OR already auto-seeded by the app:
# the TRUNCATE step removes the idempotent base-seed rows before loading, and
# seed_db.py will no-op on later boots since every record will already exist.
#
# Usage:
#   ./scripts/db_migration/load_preserved.sh "postgresql://user:pass@host:port/newdb"
# or:
#   NEW_DATABASE_URL="postgresql://..." ./scripts/db_migration/load_preserved.sh
#
# Run from the project root with the virtualenv active. Do NOT run this while
# the app is live and writing to this database - do it before pointing the app
# at the new DB, or during a maintenance window.

set -euo pipefail

NEW_URL="${1:-${NEW_DATABASE_URL:-}}"
if [[ -z "$NEW_URL" ]]; then
  echo "ERROR: pass the new database URL as arg 1, or set NEW_DATABASE_URL" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMP_FILE="$SCRIPT_DIR/preserved_data.sql"
if [[ ! -f "$DUMP_FILE" ]]; then
  echo "ERROR: $DUMP_FILE not found - run dump_preserved.sh first" >&2
  exit 1
fi

# The 17 tables the dump restores. CASCADE also clears the 4 wiped tables
# (they FK onto locations/devices); RESTART IDENTITY resets their sequences.
TRUNCATE_SQL="TRUNCATE
  admin_users, admin_audit_logs, refresh_tokens, password_reset_otps,
  locations, sensor_devices, camera_devices,
  responders, groups, responder_groups, responders_otp_verification,
  notification_templates, notification_dispatches, notification_deliveries,
  acknowledgements, push_subscriptions, system_settings
RESTART IDENTITY CASCADE;"

# Alembic + the seeder read settings.DATABASE_URL; an exported env var
# overrides the value in .env.
export DATABASE_URL="$NEW_URL"

echo "==> 1/3  Applying Alembic migrations (ensuring full schema)..."
alembic upgrade head

echo "==> 2/3  Clearing base-seed rows + 3/3 loading preserved data..."
psql "$NEW_URL" --single-transaction --set ON_ERROR_STOP=1 \
  --command="$TRUNCATE_SQL" \
  --file="$DUMP_FILE"

echo
echo "New database ready: full schema + preserved data restored."
echo "The 3 data-source tables and daily_summaries are empty."
echo
echo "Next - regenerate them with the seeder:"
echo "  DATABASE_URL=\"$NEW_URL\" python scripts/seed_dummy_readings.py"
echo
echo "Then point the app at this DB. On boot, seed_db.py will find every"
echo "base record already present and no-op."
