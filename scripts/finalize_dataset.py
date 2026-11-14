"""Finalises the generated DB: spec-conformant IDs, derived SLA breach flags, exports.
Run AFTER scripts/fix_baseline.py. Safe to re-run."""
import csv
import gzip
import hashlib
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anomaly_detector import DEFAULT_DB_PATH
from services.sla_engine import (calculate_sla_deadline, load_calendar,
                                 load_holidays, load_policy)

conn = sqlite3.connect(DEFAULT_DB_PATH)

# 1. IDs: PREFIX-<ticket-id>-NNN (the last 3 characters are the sequence).
for table, col, prefix in (("messages", "message_id", "MSG"),
                           ("assignment_events", "assignment_event_id", "ASN"),
                           ("sla_events", "sla_event_id", "SLA")):
    conn.execute(f"UPDATE {table} SET {col} = '{prefix}-' || ticket_id || '-' || substr({col}, -3)")
print("IDs normalised.")

# 2. SLA response_met: target and breach flag derived from the channel calendar.
holidays = load_holidays(conn)
anomaly = {r[0] for r in conn.execute(
    "SELECT ticket_id FROM anomaly_labels WHERE scenario_name='sla_ignores_channel_calendar'")}
cal, pol, updates, mismatch = {}, {}, [], 0
rows = conn.execute(
    "SELECT t.ticket_id, t.channel_id, t.priority, t.created_at, t.first_response_at, "
    "s.sla_event_id, s.occurred_at FROM tickets t "
    "JOIN sla_events s ON s.ticket_id=t.ticket_id AND s.event_type='response_met'").fetchall()
for tid, ch, pr, created, responded, sid, occurred in rows:
    if tid in anomaly or responded is None:
        continue
    if ch not in cal:
        cal[ch] = load_calendar(conn, ch)
    if (pr, ch) not in pol:
        pol[(pr, ch)] = load_policy(conn, pr, ch)
    due = calculate_sla_deadline(created, pol[(pr, ch)]["response_minutes"], cal[ch], holidays)
    breach = int(datetime.fromisoformat(responded) > due)
    mismatch += occurred != responded
    updates.append((due.isoformat(), breach, sid))
conn.executemany("UPDATE sla_events SET target_at=?, is_breach=? WHERE sla_event_id=?", updates)
conn.commit()
print(f"response_met rewritten: {len(updates)} (occurred_at != first_response_at: {mismatch})")
print("Breach rate by priority:", conn.execute(
    "SELECT t.priority, ROUND(100.0*SUM(s.is_breach)/COUNT(*),1) FROM sla_events s "
    "JOIN tickets t ON t.ticket_id=s.ticket_id WHERE s.event_type='response_met' "
    "GROUP BY t.priority").fetchall())

# 3. Checks for the validation summary.
print("FK violations:", len(conn.execute("PRAGMA foreign_key_check").fetchall()))
for table, col, prefix in (("messages", "message_id", "MSG-TKT-2026-"),
                           ("assignment_events", "assignment_event_id", "ASN-TKT-2026-"),
                           ("sla_events", "sla_event_id", "SLA-TKT-2026-")):
    bad = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} NOT LIKE '{prefix}%'").fetchone()[0]
    print(f"{table}: IDs not matching {prefix}*: {bad}")

# 4. Final exports (CSV per table, SQL seed, manifest with checksums).
out = Path(DEFAULT_DB_PATH).parent / "final"
out.mkdir(exist_ok=True)
manifest = {}
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
for table in tables:
    cursor = conn.execute(f"SELECT * FROM {table}")
    path = out / f"{table}.csv"
    count = 0
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([c[0] for c in cursor.description])
        for row in cursor:
            writer.writerow(row)
            count += 1
    manifest[table] = {"rows": count, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
with gzip.open(out / "seed.sql.gz", "wt", encoding="utf-8") as handle:
    for line in conn.iterdump():
        handle.write(line + "\n")
(out / "manifest.json").write_text(json.dumps(manifest, indent=2))
conn.close()
print(f"Exports written to {out}")