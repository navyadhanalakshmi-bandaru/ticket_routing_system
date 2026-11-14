"""Operational metrics computed directly from the database (deterministic, read-only)."""
import sqlite3
from datetime import datetime
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "outputs" / "ticket_routing_generated.db"
ACTIVE = ("assigned", "in_progress", "pending_customer", "queued", "reopened")


def _pct(part, whole):
    return round(100.0 * part / whole, 2) if whole else 0.0


def sla_compliance(conn):
    """Resolution-time compliance: resolved on or before the 'created' SLA target.
    Note: the 'created' target is the calendar-based RESPONSE deadline, so this is a
    proxy; the response_met events are used for response compliance below."""
    rows = conn.execute(
        "SELECT t.priority, t.channel_id, t.first_response_at, s.target_at "
        "FROM tickets t JOIN sla_events s ON s.ticket_id=t.ticket_id AND s.event_type='created' "
        "WHERE t.first_response_at IS NOT NULL").fetchall()
    overall = [0, 0]
    by_priority, by_channel = {}, {}
    for priority, channel, responded, target in rows:
        met = datetime.fromisoformat(responded) <= datetime.fromisoformat(target)
        for bucket, key in ((by_priority, priority), (by_channel, channel)):
            b = bucket.setdefault(key, [0, 0])
            b[0] += met
            b[1] += 1
        overall[0] += met
        overall[1] += 1
    fmt = lambda b: {"met": b[0], "total": b[1], "rate_pct": _pct(*b)}
    return {"overall": fmt(overall),
            "by_priority": {k: fmt(v) for k, v in sorted(by_priority.items())},
            "by_channel": {str(k): fmt(v) for k, v in sorted(by_channel.items())}}


def routing_success(conn):
    total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    assigned = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE assigned_agent_id IS NOT NULL").fetchone()[0]
    transferred = conn.execute(
        "SELECT COUNT(DISTINCT ticket_id) FROM assignment_events WHERE event_type='transfer'").fetchone()[0]
    return {"tickets": total, "assigned": assigned, "assigned_pct": _pct(assigned, total),
            "tickets_with_transfers": transferred,
            "transfer_rate_pct": _pct(transferred, total)}


def agent_utilisation(conn):
    """Current load (active tickets) vs capacity per agent."""
    marks = ",".join("?" * len(ACTIVE))
    rows = conn.execute(
        f"SELECT a.agent_id, a.max_concurrent_tickets, "
        f"SUM(CASE WHEN t.status IN ({marks}) THEN 1 ELSE 0 END) "
        f"FROM agents a LEFT JOIN tickets t ON t.assigned_agent_id=a.agent_id "
        f"GROUP BY a.agent_id", ACTIVE).fetchall()
    loads = [(agent, cap, active or 0) for agent, cap, active in rows]
    total_cap = sum(c for _, c, _ in loads)
    total_active = sum(a for _, _, a in loads)
    return {"agents": len(loads),
            "total_capacity": total_cap, "active_tickets": total_active,
            "utilisation_pct": _pct(total_active, total_cap),
            "agents_over_capacity": sum(1 for _, c, a in loads if a > c),
            "top_loaded": sorted(({"agent_id": a, "active": n, "capacity": c} for a, c, n in loads),
                                 key=lambda x: (-x["active"] / x["capacity"], x["agent_id"]))[:5]}


def status_breakdown(conn):
    return dict(conn.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status ORDER BY status"))


def breach_counts(conn):
    rows = conn.execute(
        "SELECT t.priority, COUNT(*) FROM tickets t "
        "JOIN sla_events s ON s.ticket_id=t.ticket_id AND s.event_type='created' "
        "WHERE t.first_response_at IS NOT NULL AND t.first_response_at > s.target_at "
        "GROUP BY t.priority ORDER BY t.priority").fetchall()
    return {p: n for p, n in rows}


def compute_all(db_path=None):
    conn = sqlite3.connect(db_path or DEFAULT_DB_PATH)
    try:
        return {"sla_compliance": sla_compliance(conn),
                "routing": routing_success(conn),
                "utilisation": agent_utilisation(conn),
                "status": status_breakdown(conn),
                "breaches_by_priority": breach_counts(conn)}
    finally:
        conn.close()