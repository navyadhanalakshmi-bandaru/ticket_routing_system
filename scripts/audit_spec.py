import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anomaly_detector import DEFAULT_DB_PATH

db = sqlite3.connect(DEFAULT_DB_PATH)
q = lambda s: db.execute(s).fetchall()

print("ticket date range / distinct days:", q(
    "SELECT MIN(created_at), MAX(created_at), COUNT(DISTINCT substr(created_at,1,10)) FROM tickets"))
print("\nSample primary keys:")
for (t,) in q("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
    pk = [c[1] for c in db.execute(f"PRAGMA table_info({t})") if c[5]]
    if pk:
        print(f"  {t}.{pk[0]}:", [r[0] for r in db.execute(f"SELECT {pk[0]} FROM {t} LIMIT 2")])
print("\nEvent types:")
for t in ("ticket_events", "assignment_events", "sla_events"):
    print(" ", t, q(f"SELECT event_type, COUNT(*) FROM {t} GROUP BY 1"))
print("reopened tickets:", q("SELECT COUNT(*) FROM tickets WHERE reopened_count>0"))
print("priority mix:", q("SELECT priority, COUNT(*) FROM tickets GROUP BY 1"))
print("breach flags:", q("SELECT event_type, is_breach, COUNT(*) FROM sla_events GROUP BY 1,2"))
print("\nSchemas:")
for t in ("tickets", "agents", "queues", "agent_skills", "agent_languages",
          "skill_intents", "queue_intents", "intents"):
    print(f"  {t}:", [c[1] for c in db.execute(f"PRAGMA table_info({t})")])