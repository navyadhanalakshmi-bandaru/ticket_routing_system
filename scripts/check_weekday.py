"""Routes recent queued tickets at a weekday time to prove the router works (read-only)."""
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.routing_engine import DEFAULT_DB_PATH, evaluate_ticket_routing

db = sqlite3.connect(DEFAULT_DB_PATH)
rows = db.execute("SELECT ticket_id FROM tickets WHERE status='queued' "
                  "ORDER BY created_at DESC LIMIT 15").fetchall()
db.close()

counts = Counter()
for (ticket_id,) in rows:
    r = evaluate_ticket_routing(ticket_id, routing_at="2026-11-13T11:00:00")
    counts[r["decision"]] += 1
    print(ticket_id, r["decision"], r["assigned_agent_id"], len(r["candidates"]))
print("\nDecisions:", dict(counts))