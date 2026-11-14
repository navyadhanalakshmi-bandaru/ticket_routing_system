"""Routes active/queued tickets created in working hours and shows rejection reasons (read-only)."""
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.routing_engine import DEFAULT_DB_PATH, evaluate_ticket_routing

db = sqlite3.connect(DEFAULT_DB_PATH)
rows = db.execute(
    "SELECT ticket_id, created_at FROM tickets WHERE status='queued' "
    "AND time(created_at) BETWEEN '10:00:00' AND '15:00:00' "
    "ORDER BY created_at DESC LIMIT 10").fetchall()
db.close()

counts = Counter()
for ticket_id, created_at in rows:
    r = evaluate_ticket_routing(ticket_id)
    reasons = Counter(x["reason"] for x in r["rejected_agents"])
    counts[r["decision"]] += 1
    print(f"{ticket_id} @ {created_at}: {r['decision']} | agent={r['assigned_agent_id']} "
          f"| candidates={len(r['candidates'])} | {dict(reasons)}")
print("\nDecisions:", dict(counts))