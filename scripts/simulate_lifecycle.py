"""Simulates baseline lifecycle history from documented rules (no randomness).
Run AFTER fix_baseline.py and BEFORE finalize_dataset.py. Applies once per generated DB."""
import shutil
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import END_DATE
from services.anomaly_detector import DEFAULT_DB_PATH
from services.sla_engine import ESCALATION_AFTER, escalate_ticket

ENABLE_REOPENINGS = True            # set False if reopenings cause capacity false positives
REOPEN_PRIORITIES = ("Critical", "High")
REOPEN_AFTER_MIN = 60               # customer reopens 60 min after resolution
REWORK_MIN = {"Critical": 120, "High": 240}
ORDER = {"escalated": 0, "resolved": 1, "reopened": 2, "closed": 3}

conn = sqlite3.connect(DEFAULT_DB_PATH)
if conn.execute("SELECT COUNT(*) FROM ticket_events WHERE notes LIKE 'SIM:%'").fetchone()[0]:
    print("Lifecycle already applied to this DB. Regenerate the DB to run it again.")
    sys.exit(0)
shutil.copy(DEFAULT_DB_PATH, str(DEFAULT_DB_PATH) + ".prelifecycle.bak")

end = datetime.fromisoformat(END_DATE).replace(hour=23, minute=59, second=59)
labeled = {r[0] for r in conn.execute("SELECT ticket_id FROM anomaly_labels")}
due = dict(conn.execute("SELECT ticket_id, target_at FROM sla_events WHERE event_type='created'"))
csat = dict(conn.execute("SELECT ticket_id, csat_score FROM resolutions WHERE resolution_number=1"))
base = dict(conn.execute("SELECT ticket_id, COUNT(*) FROM ticket_events GROUP BY ticket_id"))

new_events = defaultdict(list)   # ticket -> (event_at, type, old, new, actor_type, actor_id, notes)
reopen_updates, reopen_ids = [], []
n_escalate = 0

rows = conn.execute(
    "SELECT ticket_id, customer_id, priority, status, assigned_agent_id, first_response_at, "
    "resolved_at, closed_at FROM tickets ORDER BY ticket_id").fetchall()
for tid, cust, pr, status, agent, responded, resolved, closed in rows:
    if tid in labeled:
        continue
    # --- escalation: derived from the response deadline and escalate_ticket()
    if responded and tid in due:
        d, r = datetime.fromisoformat(due[tid]), datetime.fromisoformat(responded)
        if r > d:
            decision = escalate_ticket(pr, d, r)
            if decision["level"] >= 1:
                new_events[tid].append((d.isoformat(), "escalated", "assigned", "assigned",
                                        "system", "SYSTEM", "SIM: level 1 Team Lead, response deadline passed"))
                n_escalate += 1
            if decision["level"] == 2:
                at = d + timedelta(minutes=ESCALATION_AFTER[pr])
                new_events[tid].append((at.isoformat(), "escalated", "assigned", "assigned",
                                        "system", "SYSTEM",
                                        f"SIM: level 2 Priority Escalation, {ESCALATION_AFTER[pr]} min overdue"))
                n_escalate += 1
    # --- resolution / closure history
    if resolved:
        new_events[tid].append((resolved, "resolved", "in_progress", "resolved",
                                "agent", agent, "SIM: resolved"))
        if (ENABLE_REOPENINGS and status == "resolved" and not closed
                and pr in REOPEN_PRIORITIES and csat.get(tid) == 1):
            reopened_at = datetime.fromisoformat(resolved) + timedelta(minutes=REOPEN_AFTER_MIN)
            again = reopened_at + timedelta(minutes=REWORK_MIN[pr])
            if again <= end:
                new_events[tid].append((reopened_at.isoformat(), "reopened", "resolved", "reopened",
                                        "customer", cust, "SIM: customer reopened after CSAT 1"))
                new_events[tid].append((again.isoformat(), "resolved", "reopened", "resolved",
                                        "agent", agent, "SIM: resolved again after rework"))
                reopen_updates.append((again.isoformat(), tid))
                reopen_ids.append(tid)
        if closed:
            new_events[tid].append((closed, "closed", "resolved", "closed",
                                    "system", "SYSTEM", "SIM: closed"))

insert_rows = []
for tid in sorted(new_events):
    n = base.get(tid, 0)
    for at, typ, old, new, actor_type, actor_id, notes in sorted(
            new_events[tid], key=lambda e: (e[0], ORDER[e[1]])):
        n += 1
        insert_rows.append((f"EVT-{tid[-6:]}-{n:03d}", tid, typ, old, new, at, actor_type, actor_id, notes))

try:
    conn.executemany(
        "INSERT INTO ticket_events (ticket_event_id, ticket_id, event_type, old_status, new_status, "
        "event_at, actor_type, actor_id, notes) VALUES (?,?,?,?,?,?,?,?,?)", insert_rows)
    # second resolution row for reopened tickets (history kept: resolution 1 is not touched)
    cols = [c[1] for c in conn.execute("PRAGMA table_info(resolutions)")]
    for resolved_again, tid in reopen_updates:
        row = dict(zip(cols, conn.execute(
            "SELECT * FROM resolutions WHERE ticket_id=? AND resolution_number=1", (tid,)).fetchone()))
        row.update(resolution_id=f"RES-{tid[-6:]}-002", resolution_number=2,
                   resolved_at=resolved_again, csat_score=None, customer_feedback=None)
        conn.execute(f"INSERT INTO resolutions ({','.join(cols)}) VALUES ({','.join(':' + c for c in cols)})", row)
        conn.execute("UPDATE tickets SET reopened_count=1, resolved_at=? WHERE ticket_id=?",
                     (resolved_again, tid))
    conn.commit()
except sqlite3.IntegrityError as error:
    conn.rollback()
    print("FAILED, nothing was changed:", error)
    sys.exit(1)

print(f"Events inserted: {len(insert_rows)} (escalations: {n_escalate}); reopened tickets: {len(reopen_ids)}")
print("FK violations:", len(conn.execute("PRAGMA foreign_key_check").fetchall()))
conn.close()