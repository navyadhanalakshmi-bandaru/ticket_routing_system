import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anomaly_detector import DEFAULT_DB_PATH

print("Database used:", DEFAULT_DB_PATH)
db = sqlite3.connect(DEFAULT_DB_PATH)
q = lambda s: db.execute(s).fetchall()

print("Row count tickets:", q("SELECT COUNT(*) FROM tickets"))
print("Tickets with no 'created' event:", q(
    "SELECT ticket_id FROM tickets WHERE ticket_id NOT IN "
    "(SELECT ticket_id FROM ticket_events WHERE event_type = 'created')"))
print("Tickets with no 'assigned' event:", q(
    "SELECT ticket_id FROM tickets WHERE ticket_id NOT IN "
    "(SELECT ticket_id FROM ticket_events WHERE event_type = 'assigned')"))
print("Ticket statuses:", q("SELECT status, COUNT(*) FROM tickets GROUP BY 1"))
print("Escalated tickets by priority:", q(
    "SELECT t.priority, COUNT(DISTINCT e.ticket_id) FROM ticket_events e "
    "JOIN tickets t ON t.ticket_id = e.ticket_id WHERE e.event_type = 'escalated' GROUP BY 1"))