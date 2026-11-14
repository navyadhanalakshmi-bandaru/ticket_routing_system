from datetime import date, datetime

from services.sla_engine import (calculate_business_minutes, calculate_sla_deadline,
                                 check_sla_status, detect_sla_breach, escalate_ticket)

D = datetime.fromisoformat
# 2026-11-09 Monday, 11-13 Friday, 11-14 Saturday, 11-15 Sunday.
EMAIL = {0: (540, 1020), 1: (540, 1020), 2: (540, 1020), 3: (540, 1020),
         4: (540, 1020), 5: (540, 780), 6: None}
CHAT = {i: (0, 1440) for i in range(7)}


def test_normal_working_hours():
    assert calculate_sla_deadline("2026-11-09T10:00:00", 60, EMAIL) == D("2026-11-09T11:00:00")


def test_after_hours_waits_for_opening():
    assert calculate_sla_deadline("2026-11-13T18:00:00", 60, EMAIL) == D("2026-11-14T10:00:00")


def test_different_channel_calendars():
    start = "2026-11-13T18:00:00"
    assert calculate_sla_deadline(start, 60, CHAT) == D("2026-11-13T19:00:00")
    assert calculate_sla_deadline(start, 60, EMAIL) != calculate_sla_deadline(start, 60, CHAT)


def test_critical_short_target():
    assert calculate_sla_deadline("2026-11-09T09:00:00", 5, EMAIL) == D("2026-11-09T09:05:00")


def test_business_minutes_across_weekend():
    assert calculate_business_minutes("2026-11-14T12:00:00", "2026-11-16T10:00:00", EMAIL) == 120
    assert calculate_business_minutes("2026-11-13T16:00:00", "2026-11-14T10:00:00", EMAIL) == 120


def test_holiday_skipped():
    holidays = frozenset({date(2026, 11, 14)})
    assert calculate_sla_deadline("2026-11-13T16:00:00", 120, EMAIL, holidays) == D("2026-11-16T10:00:00")


def test_breach_detection():
    assert detect_sla_breach("2026-11-09T11:00:00", completed_at="2026-11-09T11:01:00")
    assert not detect_sla_breach("2026-11-09T11:00:00", completed_at="2026-11-09T11:00:00")


def test_status_values():
    deadline, start = "2026-11-09T11:00:00", "2026-11-09T10:00:00"
    assert check_sla_status(start, deadline, EMAIL, completed_at="2026-11-09T10:30:00") == "MET"
    assert check_sla_status(start, deadline, EMAIL, now="2026-11-09T10:50:00") == "AT_RISK"
    assert check_sla_status(start, deadline, EMAIL, now="2026-11-09T10:10:00") == "ON_TRACK"
    assert check_sla_status(start, deadline, EMAIL, now="2026-11-09T11:30:00") == "BREACHED"


def test_reopened_ticket_restarts_clock():
    original = calculate_sla_deadline("2026-11-09T10:00:00", 60, EMAIL)
    restarted = calculate_sla_deadline("2026-11-10T10:00:00", 60, EMAIL)
    assert restarted == D("2026-11-10T11:00:00") and restarted > original


def test_escalation_levels():
    assert not escalate_ticket("High", "2026-11-09T11:00:00", "2026-11-09T10:00:00")["escalate"]
    assert escalate_ticket("High", "2026-11-09T11:00:00", "2026-11-09T11:30:00")["level"] == 1
    result = escalate_ticket("Critical", "2026-11-09T11:00:00", "2026-11-09T11:20:00")
    assert result["level"] == 2 and result["target"] == "Priority Escalation"


def test_deterministic():
    a = calculate_sla_deadline("2026-11-13T18:00:00", 480, EMAIL)
    assert a == calculate_sla_deadline("2026-11-13T18:00:00", 480, EMAIL)