#!/usr/bin/env bash
# restore.sh - Production MySQL restore script for Hedgewar Hospital Care (R-05)
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <path_to_backup.sql.gz> [target_db_name]"
  exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="${2:-${DB_NAME:-hms_test}}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-hms_user}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Error: Backup file '${BACKUP_FILE}' not found."
  exit 1
fi

CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [ -f "${CHECKSUM_FILE}" ]; then
  echo "Verifying SHA256 integrity checksum..."
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c "${CHECKSUM_FILE}"
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "${CHECKSUM_FILE}"
  fi
  echo "Checksum verified: Integrity OK."
else
  echo "Warning: Checksum file not found, proceeding without verification."
fi

echo "=== Target Database: ${TARGET_DB} on ${DB_HOST}:${DB_PORT} ==="
echo "Restoring from: ${BACKUP_FILE}"

if [ -n "${DB_PASSWORD:-}" ]; then
  export MYSQL_PWD="${DB_PASSWORD}"
fi

# Decompress and stream into target database
gzip -dc "${BACKUP_FILE}" | mysql \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --user="${DB_USER}" \
  --default-character-set=utf8mb4 \
  "${TARGET_DB}"

echo "Database restored successfully into '${TARGET_DB}'."

# Verification check
echo "Running post-restore sanity check..."
mysql \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --user="${DB_USER}" \
  --default-character-set=utf8mb4 \
  -e "SELECT 'Users' AS entity, count(*) AS count FROM user UNION SELECT 'Rooms', count(*) FROM room UNION SELECT 'Appointments', count(*) FROM appointments;" \
  "${TARGET_DB}"
