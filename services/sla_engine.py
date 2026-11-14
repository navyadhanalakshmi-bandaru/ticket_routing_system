"""SLA engine: deterministic, calendar-aware deadlines (no randomness, no wall clock)."""
import sqlite3
from datetime import date, datetime, time, timedelta

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday",
             "friday", "saturday", "sunday"]
MAX_SEARCH_DAYS = 400
WARNING_RATIO = 0.80

# Overdue minutes after which the ticket moves to the next escalation level.
ESCALATION_AFTER = {"Critical": 15, "High": 60, "Medium": 240, "Low": 480}


def _to_minutes(value):
    """'09:00' -> 540. '23:59' is treated as end of day (1440) for 24h calendars."""
    if value is None:
        return None
    if value == "23:59":
        return 1440
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _parse(value):
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


# ---------------------------------------------------------------- loading
def _rows(connection, sql, params=()):
    cursor = connection.execute(sql, params)
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def load_calendar(connection, channel_id):
    """Return {weekday_index: (open_min, close_min) or None} for a channel."""
    rows = _rows(
        connection,
        """SELECT bc.* FROM business_calendars bc
           JOIN channel_calendars cc ON cc.calendar_id = bc.calendar_id
           WHERE cc.channel_id = ?""",
        (channel_id,),
    )
    if not rows:
        raise ValueError(f"No calendar for channel {channel_id}")
    row = rows[0]
    calendar = {}
    for index, name in enumerate(DAY_NAMES):
        opens, closes = row[f"{name}_open"], row[f"{name}_close"]
        calendar[index] = (
            (_to_minutes(opens), _to_minutes(closes)) if opens and closes else None
        )
    return calendar


def load_holidays(connection):
    """Holiday dates (the table is empty by default; column name is assumed)."""
    try:
        rows = connection.execute("SELECT holiday_date FROM calendar_holidays").fetchall()
    except sqlite3.Error:
        return frozenset()
    return frozenset(date.fromisoformat(str(r[0])[:10]) for r in rows)


def load_policy(connection, priority, channel_id):
    rows = _rows(
        connection,
        """SELECT response_minutes, resolution_minutes FROM sla_policies
           WHERE priority = ? AND channel_id = ? AND is_active = 1""",
        (priority, channel_id),
    )
    if not rows:
        raise ValueError(f"No SLA policy for {priority}/channel {channel_id}")
    return rows[0]


# ---------------------------------------------------------------- core maths
def _window(day, calendar):
    """Open/close datetimes for a day, or None."""
    spec = calendar.get(day.weekday())
    if not spec:
        return None
    midnight = datetime.combine(day, time())
    return midnight + timedelta(minutes=spec[0]), midnight + timedelta(minutes=spec[1])


def calculate_business_minutes(start, end, calendar, holidays=frozenset()):
    """Minutes between start and end that fall inside the channel calendar."""
    start, end = _parse(start), _parse(end)
    if end <= start:
        return 0.0
    total = 0.0
    day = start.date()
    while day <= end.date():
        window = None if day in holidays else _window(day, calendar)
        if window:
            low, high = max(window[0], start), min(window[1], end)
            if high > low:
                total += (high - low).total_seconds() / 60
        day += timedelta(days=1)
    return total


def calculate_sla_deadline(start, minutes, calendar, holidays=frozenset()):
    """Deadline after `minutes` of BUSINESS time. After-hours starts wait for opening."""
    start = _parse(start)
    remaining = float(minutes)
    day = start.date()
    for _ in range(MAX_SEARCH_DAYS):
        window = None if day in holidays else _window(day, calendar)
        if window:
            begin = max(window[0], start)
            if begin < window[1]:
                available = (window[1] - begin).total_seconds() / 60
                if remaining <= available:
                    return begin + timedelta(minutes=remaining)
                remaining -= available
        day += timedelta(days=1)
    raise ValueError("No deadline found: calendar has no working time")


def detect_sla_breach(deadline, completed_at=None, now=None):
    """True if completed after the deadline (or still open and past it)."""
    reference = completed_at if completed_at is not None else now
    if reference is None:
        raise ValueError("Provide completed_at or now")
    return _parse(reference) > _parse(deadline)


def check_sla_status(start, deadline, calendar, completed_at=None, now=None,
                     holidays=frozenset(), warning_ratio=WARNING_RATIO):
    """MET | BREACHED | AT_RISK | ON_TRACK, using business minutes for the ratio."""
    deadline = _parse(deadline)
    if completed_at is not None:
        return "BREACHED" if detect_sla_breach(deadline, completed_at=completed_at) else "MET"
    if now is None:
        raise ValueError("Provide completed_at or now")
    if detect_sla_breach(deadline, now=now):
        return "BREACHED"
    total = calculate_business_minutes(start, deadline, calendar, holidays)
    used = calculate_business_minutes(start, now, calendar, holidays)
    return "AT_RISK" if total > 0 and used / total >= warning_ratio else "ON_TRACK"


def escalate_ticket(priority, deadline, now, current_level=0):
    """Return the escalation decision. Level 0 none, 1 team lead, 2 priority escalation queue."""
    overdue = (_parse(now) - _parse(deadline)).total_seconds() / 60
    if overdue <= 0:
        return {"level": current_level, "escalate": False, "overdue_minutes": 0.0,
                "target": None, "reason": "Within SLA"}
    level = 2 if overdue >= ESCALATION_AFTER[priority] else 1
    level = max(level, current_level)
    target = "Priority Escalation" if level == 2 else "Team Lead"
    return {"level": level, "escalate": level > current_level,
            "overdue_minutes": round(overdue, 1), "target": target,
            "reason": f"{priority} ticket {overdue:.0f} min past SLA "
                      f"(escalate to queue after {ESCALATION_AFTER[priority]} min)"}


# ---------------------------------------------------------------- DB helper
def expected_deadlines(connection, ticket, start=None):
    """Recompute response/resolution deadlines from source records (not random).
    Pass `start` (reopen time) to restart the clock for a reopened ticket."""
    calendar = load_calendar(connection, ticket["channel_id"])
    holidays = load_holidays(connection)
    policy = load_policy(connection, ticket["priority"], ticket["channel_id"])
    start = start or ticket["created_at"]
    return {
        "response_due": calculate_sla_deadline(start, policy["response_minutes"], calendar, holidays),
        "resolution_due": calculate_sla_deadline(start, policy["resolution_minutes"], calendar, holidays),
    }