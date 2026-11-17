# Hedgewar Hospital Care — Database Backup and Disaster Recovery Runbook (R-05)

## 1. Objectives & SLAs
- **Recovery Point Objective (RPO):** $< 1\text{ hour}$ (maximum allowable data loss in disaster).
- **Recovery Time Objective (RTO):** $< 30\text{ minutes}$ (maximum duration to restore full operational service).
- **Compliance & Privacy:** Backups contain clinical and financial records. All backups at rest and in transit must be encrypted using AES-256 and stored on access-controlled storage.

---

## 2. Backup Strategy

### A. Logical Snapshots (Daily / Scheduled)
Executed via `scripts/backup.sh`:
- Non-blocking InnoDB consistent snapshot (`--single-transaction`).
- UTF-8 Multi-byte support (`--default-character-set=utf8mb4`).
- Routines and triggers preserved (`--routines --triggers`).
- Memory-safe streaming (`--quick`).
- Table-space privilege decoupling (`--no-tablespaces`).
- Maximum compression (`gzip -9`).
- Cryptographic integrity verification via SHA-256 checksums.

```bash
# Manual execution
DB_PASSWORD="<password>" ./scripts/backup.sh

# Cron automation (e.g. daily at 02:00 UTC)
0 2 * * * DB_PASSWORD="<password>" /opt/hedgewar-hms/scripts/backup.sh >> /var/log/hms-backup.log 2>&1
```

### B. Point-in-Time Recovery (PITR) via Binary Logs
In production `my.cnf`:
```ini
[mysqld]
log-bin=mysql-bin
binlog_format=ROW
binlog_row_image=FULL
binlog_expire_logs_seconds=604800 # 7 days retention
```
In the event of accidental data corruption at 14:15:
1. Restore previous night's logical backup (e.g. 02:00).
2. Replay binary logs up to 14:14:59:
   ```bash
   mysqlbinlog --stop-datetime="2026-11-17 14:14:59" /var/lib/mysql/mysql-bin.0000* | mysql -u hms_user -p hms_prod
   ```

---

## 3. Restoration Drill (Step-by-Step)

### Step 1: Pre-Restoration Verification
1. Confirm the backup archive and `.sha256` checksum are present.
2. Verify integrity:
   ```bash
   shasum -a 256 -c hedgewar_hms_hms_test_20261117_162748.sql.gz.sha256
   ```

### Step 2: Provision Staging / Recovery Database
Never restore directly over active production without testing on an isolated database first:
```sql
CREATE DATABASE hms_restore_drill CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON hms_restore_drill.* TO 'hms_user'@'%';
FLUSH PRIVILEGES;
```

### Step 3: Stream Restoration
```bash
DB_PASSWORD="<password>" ./scripts/restore.sh ./backups/hedgewar_hms_hms_test_20261117_162748.sql.gz hms_restore_drill
```

### Step 4: Sanity & Parity Audit
Verify key relational entities:
```sql
SELECT 'Users' AS entity, count(*) AS count FROM hms_restore_drill.user
UNION ALL
SELECT 'Doctors', count(*) FROM hms_restore_drill.doctor
UNION ALL
SELECT 'Appointments', count(*) FROM hms_restore_drill.appointments
UNION ALL
SELECT 'Invoices', count(*) FROM hms_restore_drill.invoice
UNION ALL
SELECT 'Rooms', count(*) FROM hms_restore_drill.room;
```

---

## 4. Migration Downgrade & Rollback Drill

Before deploying any schema migration to production, test bidirectional compatibility:

1. **Verify current head:**
   ```bash
   flask db current
   ```
2. **Execute one-step downgrade:**
   ```bash
   flask db downgrade -1
   ```
3. **Verify schema stability and inspect tables:**
   ```bash
   pytest tests/integration/test_ddl_parity.py
   ```
4. **Re-upgrade back to head:**
   ```bash
   flask db upgrade
   ```
5. **Verify health endpoint:**
   ```bash
   curl -s http://localhost:8000/readyz
   ```
   Should return: `{"status": "ready", "database": "connected", "migrations": "at_head"}`.
