import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anomaly_detector import DEFAULT_DB_PATH
db = sqlite3.connect(DEFAULT_DB_PATH)
t = "TKT-2026-021053"
for tbl in ("tickets", "ticket_events", "assignment_events", "sla_events", "resolutions", "anomaly_labels"):
    print(tbl, db.execute(f"SELECT * FROM {tbl} WHERE ticket_id = ?", (t,)).fetchall())