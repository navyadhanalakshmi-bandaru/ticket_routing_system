import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anomaly_detector import DEFAULT_DB_PATH
from services.sla_engine import calculate_sla_deadline, load_calendar, load_holidays, load_policy

conn = sqlite3.connect(DEFAULT_DB_PATH)
print("sla_events columns:", [c[1] for c in conn.execute("PRAGMA table_info(sla_events)")])
print("sla event types:", conn.execute(
    "SELECT event_type, COUNT(*) FROM sla_events GROUP BY event_type").fetchall())

# 1. How does the stored 'created' target relate to created_at?
holidays = load_holidays(conn)
rows = conn.execute(
    "SELECT t.ticket_id, t.channel_id, t.priority, t.created_at, s.target_at "
    "FROM tickets t JOIN sla_events s ON s.ticket_id=t.ticket_id AND s.event_type='created' "
    "LIMIT 3000").fetchall()
stored_gap, resp_gap, res_gap = Counter(), Counter(), Counter()
shown = 0
for tid, ch, pr, created, target in rows:
    cal, pol = load_calendar(conn, ch), load_policy(conn, pr, ch)
    gap = round((datetime.fromisoformat(target) - datetime.fromisoformat(created)).total_seconds() / 60)
    stored_gap[gap] += 1
    exp_resp = calculate_sla_deadline(created, pol["response_minutes"], cal, holidays)
    exp_res = calculate_sla_deadline(created, pol["resolution_minutes"], cal, holidays)
    resp_gap[abs(datetime.fromisoformat(target) - exp_resp).total_seconds() < 60] += 1
    res_gap[abs(datetime.fromisoformat(target) - exp_res).total_seconds() < 60] += 1
    if shown < 5:
        print(tid, ch, pr, "created", created, "stored", target,
              "| exp_resp", exp_resp.isoformat(), "| exp_res", exp_res.isoformat())
        shown += 1
print("\nMost common stored gaps (minutes):", stored_gap.most_common(8))
print("Matches response calendar deadline:", dict(resp_gap))
print("Matches resolution calendar deadline:", dict(res_gap))

# 2. Capacity: how overloaded do agents get?
print("\nTickets per agent vs capacity (top 8 by ticket count):")
for r in conn.execute(
        "SELECT a.agent_id, a.max_concurrent_tickets, COUNT(*) c FROM tickets t "
        "JOIN agents a ON a.agent_id=t.assigned_agent_id GROUP BY a.agent_id "
        "ORDER BY c DESC LIMIT 8"):
    print(r)
print("Ticket status counts:", conn.execute(
    "SELECT status, COUNT(*) FROM tickets GROUP BY status").fetchall())