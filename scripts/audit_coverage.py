import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anomaly_detector import DEFAULT_DB_PATH

db = sqlite3.connect(DEFAULT_DB_PATH)
q = lambda s: db.execute(s).fetchall()

print("Tickets/day min, avg, max:", q(
    "SELECT MIN(c), ROUND(AVG(c),1), MAX(c) FROM (SELECT COUNT(*) c FROM tickets GROUP BY substr(created_at,1,10))"))
print("Busiest 5 days:", q(
    "SELECT substr(created_at,1,10) d, COUNT(*) FROM tickets GROUP BY d ORDER BY 2 DESC LIMIT 5"))
print("Queue daily load (queue, max, avg):", q(
    "SELECT queue_id, MAX(c), ROUND(AVG(c),1) FROM (SELECT queue_id, COUNT(*) c FROM tickets "
    "GROUP BY queue_id, substr(created_at,1,10)) GROUP BY queue_id"))
print("Critical per day (min, avg, max):", q(
    "SELECT MIN(c), ROUND(AVG(c),1), MAX(c) FROM (SELECT COUNT(*) c FROM tickets "
    "WHERE priority='Critical' GROUP BY substr(created_at,1,10))"))
print("Channel mix:", q("SELECT channel_id, COUNT(*) FROM tickets GROUP BY 1"))
print("Language mix:", q("SELECT language_id, COUNT(*) FROM tickets GROUP BY 1"))
print("Agents per language (proficiency>=3):", q(
    "SELECT language_id, COUNT(*) FROM agent_languages WHERE proficiency>=3 GROUP BY 1"))
print("Messages per ticket (min, avg, max):", q(
    "SELECT MIN(c), ROUND(AVG(c),1), MAX(c) FROM (SELECT COUNT(*) c FROM messages GROUP BY ticket_id)"))
print("Message columns:", [c[1] for c in db.execute("PRAGMA table_info(messages)")])
print("Ticket event types:", q("SELECT event_type, COUNT(*) FROM ticket_events GROUP BY 1"))
print("Assignment event types:", q("SELECT event_type, COUNT(*) FROM assignment_events GROUP BY 1"))
print("Customer columns:", [c[1] for c in db.execute("PRAGMA table_info(customers)")])

hours, after, total = Counter(), Counter(), Counter()
for channel, at in q("SELECT channel_id, created_at FROM tickets"):
    t = datetime.fromisoformat(at)
    w = t.weekday()
    outside = (w == 6 or (w == 5 and (t.hour < 9 or t.hour >= 13))
               or (w < 5 and (t.hour < 9 or t.hour >= 17)))
    hours[t.hour] += 1
    total[channel] += 1
    after[channel] += outside
print("Arrivals by hour:", [hours[h] for h in range(24)])
print("Outside email/phone business hours, by channel (after, total):",
      {c: (after[c], total[c]) for c in sorted(total)})