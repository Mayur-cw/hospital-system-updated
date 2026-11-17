#!/usr/bin/env bash
# backup.sh - Production MySQL backup script for Hedgewar Hospital Care (R-05)
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-hms_user}"
DB_NAME="${DB_NAME:-hms_test}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "${BACKUP_DIR}"

BACKUP_FILE="${BACKUP_DIR}/hedgewar_hms_${DB_NAME}_${TIMESTAMP}.sql.gz"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"

echo "=== Starting Hedgewar HMS Backup: ${TIMESTAMP} ==="
echo "Target: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "Output: ${BACKUP_FILE}"

# Export MySQL password safely if provided
if [ -n "${DB_PASSWORD:-}" ]; then
  export MYSQL_PWD="${DB_PASSWORD}"
fi

# Execute non-blocking transactional mysqldump
mysqldump \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --user="${DB_USER}" \
  --single-transaction \
  --quick \
  --no-tablespaces \
  --routines \
  --triggers \
  --set-gtid-purged=OFF \
  --hex-blob \
  --default-character-set=utf8mb4 \
  "${DB_NAME}" | gzip -9 > "${BACKUP_FILE}"

# Generate SHA256 integrity checksum
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${BACKUP_FILE}" > "${CHECKSUM_FILE}"
elif command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${BACKUP_FILE}" > "${CHECKSUM_FILE}"
fi

echo "Backup completed successfully."
echo "Checksum: $(cat "${CHECKSUM_FILE}")"

# Prune old backups
find "${BACKUP_DIR}" -name "hedgewar_hms_*.sql.gz*" -mtime +"${RETENTION_DAYS}" -exec rm -f {} +
echo "Retention policy enforced (retained last ${RETENTION_DAYS} days)."
