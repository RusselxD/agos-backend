#!/usr/bin/env bash
#
# Step 1 of the DB reset: dump the data we want to KEEP from the current
# (old) Railway database into a data-only SQL file.
#
# Preserved : admins, responders, locations/devices, notifications, settings,
#             etc. (17 tables - see PRESERVE_TABLES below)
# NOT dumped: sensor_readings, model_readings, weather, daily_summaries
#             -> these are regenerated later by scripts/seed_dummy_readings.py
#
# Usage:
#   ./scripts/db_migration/dump_preserved.sh "postgresql://user:pass@host:port/db"
# or:
#   OLD_DATABASE_URL="postgresql://..." ./scripts/db_migration/dump_preserved.sh
#
# Use the Railway PUBLIC database URL (the externally reachable one).
#
# pg_dump must be >= the server's Postgres major version. If your local
# pg_dump is too old, run it through Docker instead:
#   DUMP_VIA_DOCKER=1 ./scripts/db_migration/dump_preserved.sh "postgresql://..."
# Override the image (defaults to the server's major version) with:
#   PG_DOCKER_IMAGE=postgres:18 DUMP_VIA_DOCKER=1 ./scripts/...

set -euo pipefail

OLD_URL="${1:-${OLD_DATABASE_URL:-}}"
if [[ -z "$OLD_URL" ]]; then
  echo "ERROR: pass the old database URL as arg 1, or set OLD_DATABASE_URL" >&2
  exit 1
fi

OUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_FILE="$OUT_DIR/preserved_data.sql"

DUMP_VIA_DOCKER="${DUMP_VIA_DOCKER:-0}"
PG_DOCKER_IMAGE="${PG_DOCKER_IMAGE:-postgres:18}"

# Everything EXCEPT sensor_readings / model_readings / weather / daily_summaries.
PRESERVE_TABLES=(
  admin_users
  admin_audit_logs
  refresh_tokens
  password_reset_otps
  locations
  sensor_devices
  camera_devices
  responders
  groups
  responder_groups
  responders_otp_verification
  notification_templates
  notification_dispatches
  notification_deliveries
  acknowledgements
  push_subscriptions
  system_settings
)

# Shared pg_dump arguments (no --file: output goes to stdout, redirected below).
DUMP_ARGS=( "$OLD_URL" --data-only --no-owner --no-privileges --disable-triggers )
for t in "${PRESERVE_TABLES[@]}"; do
  DUMP_ARGS+=( --table="public.$t" )
done

echo "Dumping ${#PRESERVE_TABLES[@]} preserved tables from the old database..."

if [[ "$DUMP_VIA_DOCKER" == "1" ]]; then
  echo "(using $PG_DOCKER_IMAGE via Docker)"
  docker run --rm "$PG_DOCKER_IMAGE" pg_dump "${DUMP_ARGS[@]}" > "$OUT_FILE"
else
  pg_dump "${DUMP_ARGS[@]}" > "$OUT_FILE"
fi

echo
echo "Done -> $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
echo "Next: provision the new database, then run load_preserved.sh against it."
