import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.routing_engine import DEFAULT_DB_PATH

db = sqlite3.connect(DEFAULT_DB_PATH)
for table in ["sla_events", "ticket_events", "assignment_events", "resolutions", "calendar_holidays"]:
    print(f"\n--- {table} ---")
    print([c[1] for c in db.execute(f"PRAGMA table_info({table})")])
print("\nSLA event types:", db.execute("SELECT event_type, COUNT(*) FROM sla_events GROUP BY event_type").fetchall())
print("Ticket event types:", db.execute("SELECT event_type, COUNT(*) FROM ticket_events GROUP BY event_type").fetchall())
print("Assignment event types:", db.execute("SELECT event_type, COUNT(*) FROM assignment_events GROUP BY event_type").fetchall())