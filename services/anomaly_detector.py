"""Five anomaly detectors. Reads operational tables ONLY (never ground truth)."""
import csv
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from services.sla_engine import (calculate_sla_deadline, load_calendar,
                                 load_holidays, load_policy)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "outputs" / "ticket_routing_generated.db"
SLA_TOLERANCE_MIN = 1.0


def _finding(ticket_id, issue_type, description, severity, expected, actual, action):
    return {"ticket_id": ticket_id, "issue_type": issue_type, "description": description,
            "severity": severity, "expected_behaviour": expected,
            "actual_behaviour": actual, "detection_status": "DETECTED",
            "recommended_action": action}


def detect_capacity_violations(conn):
    """Sweep each agent's assignment intervals; flag the ticket that pushes load over capacity."""
    capacity = dict(conn.execute("SELECT agent_id, max_concurrent_tickets FROM agents"))
    resolved = dict(conn.execute("SELECT ticket_id, resolved_at FROM tickets"))
    by_ticket = defaultdict(list)
    for ticket_id, agent_id, at in conn.execute(
            "SELECT ticket_id, to_agent_id, assigned_at FROM assignment_events "
            "ORDER BY ticket_id, assigned_at, assignment_event_id"):
        by_ticket[ticket_id].append((agent_id, datetime.fromisoformat(at)))

    points = defaultdict(list)  # agent -> [(time, kind, ticket)], kind 0=end, 1=start
    for ticket_id, events in by_ticket.items():
        final_end = datetime.fromisoformat(resolved[ticket_id]) if resolved[ticket_id] else datetime.max
        for i, (agent_id, start) in enumerate(events):
            end = events[i + 1][1] if i + 1 < len(events) else final_end
            if end > start:
                points[agent_id].append((start, 1, ticket_id))
                points[agent_id].append((end, 0, ticket_id))

    findings, flagged = [], set()
    for agent_id, pts in points.items():
        active = 0
        for when, kind, ticket_id in sorted(pts):
            active += 1 if kind else -1
            if kind and active > capacity[agent_id] and ticket_id not in flagged:
                flagged.add(ticket_id)
                findings.append(_finding(
                    ticket_id, "agent_over_capacity",
                    f"{agent_id} holds {active} concurrent tickets at {when.isoformat()}",
                    "High", f"At most {capacity[agent_id]} concurrent tickets per agent",
                    f"{active} concurrent tickets", "Reassign to an agent with free capacity"))
    return findings


def detect_sla_calendar_errors(conn):
    """Recompute the response deadline from the channel calendar and compare."""
    cache, findings = {}, []
    holidays = load_holidays(conn)
    rows = conn.execute(
        "SELECT t.ticket_id, t.channel_id, t.priority, t.created_at, s.target_at "
        "FROM tickets t JOIN sla_events s ON s.ticket_id = t.ticket_id AND s.event_type = 'created'")
    for ticket_id, channel_id, priority, created_at, target_at in rows:
        if channel_id not in cache:
            cache[channel_id] = load_calendar(conn, channel_id)
        if (priority, channel_id) not in cache:
            cache[(priority, channel_id)] = load_policy(conn, priority, channel_id)
        expected = calculate_sla_deadline(
            created_at, cache[(priority, channel_id)]["response_minutes"], cache[channel_id], holidays)
        actual = datetime.fromisoformat(target_at)
        diff = abs((actual - expected).total_seconds()) / 60
        if diff > SLA_TOLERANCE_MIN:
            findings.append(_finding(
                ticket_id, "sla_ignores_channel_calendar",
                f"Stored response deadline differs from calendar-based deadline by {diff:.0f} min",
                "Medium", f"Deadline {expected.isoformat()} (channel business hours)",
                f"Deadline {actual.isoformat()}", "Recalculate the SLA using the channel calendar"))
    return findings


def detect_reopen_history_loss(conn):
    """A reopened ticket must still have its earlier lifecycle events."""
    findings = []
    rows = conn.execute(
        "SELECT t.ticket_id, COUNT(e.ticket_event_id) FROM tickets t "
        "LEFT JOIN ticket_events e ON e.ticket_id = t.ticket_id "
        "WHERE t.reopened_count > 0 OR t.status = 'reopened' GROUP BY t.ticket_id")
    for ticket_id, event_count in rows:
        if event_count < 2:
            findings.append(_finding(
                ticket_id, "reopened_ticket_loses_history",
                f"Reopened ticket has only {event_count} lifecycle event(s)",
                "High", "Created and assigned history preserved after reopening",
                f"{event_count} events", "Restore events from audit log; never delete history"))
    return findings


def detect_transfer_loops(conn):
    """Flag a ticket that is transferred back to an agent who already held it."""
    chains = defaultdict(list)
    for ticket_id, source, target in conn.execute(
            "SELECT ticket_id, from_agent_id, to_agent_id FROM assignment_events "
            "WHERE event_type = 'transfer' ORDER BY ticket_id, assigned_at, assignment_event_id"):
        chains[ticket_id].append((source, target))
    findings = []
    for ticket_id, chain in chains.items():
        seen = {chain[0][0]}
        for step, (_, target) in enumerate(chain, start=1):
            if target in seen:
                path = " -> ".join([chain[0][0]] + [t for _, t in chain])
                findings.append(_finding(
                    ticket_id, "transfer_loop", f"Transfer path revisits an agent: {path}",
                    "Medium", "Each agent appears at most once in a transfer path",
                    f"{len(chain)} transfers, agent {target} repeated at step {step}",
                    "Block transfers to previous holders; escalate to a team lead"))
                break
            seen.add(target)
    return findings


def detect_priority_violations(conn):
    """Safety-related intents must be Critical."""
    findings = []
    rows = conn.execute(
        "SELECT t.ticket_id, t.priority, i.intent_name FROM tickets t "
        "JOIN intents i ON i.intent_id = t.intent_id "
        "WHERE i.is_safety_related = 1 AND t.priority <> 'Critical'")
    for ticket_id, priority, intent_name in rows:
        findings.append(_finding(
            ticket_id, "priority_contradicts_safety_rule",
            f"'{intent_name}' ticket has priority {priority}",
            "Critical", "Safety-related intents are always Critical", f"Priority {priority}",
            "Raise priority to Critical and re-route to the security queue"))
    return findings


def run_all_detectors(db_path=None, report_path=None):
    conn = sqlite3.connect(db_path or DEFAULT_DB_PATH)
    try:
        findings = (detect_capacity_violations(conn) + detect_sla_calendar_errors(conn)
                    + detect_reopen_history_loss(conn) + detect_transfer_loops(conn)
                    + detect_priority_violations(conn))
    finally:
        conn.close()
    findings.sort(key=lambda f: (f["issue_type"], f["ticket_id"]))
    for n, finding in enumerate(findings, start=1):
        finding["anomaly_id"] = f"DET-{n:06d}"
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        columns = ["anomaly_id", "ticket_id", "issue_type", "description", "severity",
                   "expected_behaviour", "actual_behaviour", "detection_status", "recommended_action"]
        with open(report_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(findings)
    return findings