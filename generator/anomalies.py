from datetime import datetime, timedelta

from config.settings import END_DATE, RANDOM_SEED
from generator.normalize import normalize_workload


def inject_anomalies(transactions, master_data):
    """Inject five labelled anomalies into synthetic transactions.

    First makes ticket status depend on ticket age (normalize_workload),
    so old tickets are resolved/closed and only recent tickets stay active.
    Then injects the five labelled anomalies.
    """

    agents = master_data["agents"]
    intents = master_data["intents"]

    if len(transactions["tickets"]) < 20 or len(agents) < 2:
        raise ValueError("Not enough tickets or agents for anomaly injection.")

    # Baseline must be valid BEFORE any anomaly is injected.
    normalize_workload(transactions, master_data, END_DATE, RANDOM_SEED)
    tickets = transactions["tickets"]

    labels = []
    used = set()

    def label(ticket, scenario, issue):
        labels.append({
            "anomaly_id": f"ANM-{len(labels) + 1:06d}",
            "ticket_id": ticket["ticket_id"],
            "scenario_name": scenario,
            "expected_issue": issue,
        })
        used.add(ticket["ticket_id"])

    # Oldest-first order, deterministic (created_at, then ticket_id).
    ordered = sorted(tickets, key=lambda t: (t["created_at"], t["ticket_id"]))

    # ------------------------------------------------------------------
    # 1. Agent over capacity
    # Use the NEWEST capacity+1 tickets so they genuinely overlap in time
    # (all active at once, none resolved).
    # ------------------------------------------------------------------
    agent = agents[0]
    capacity = int(agent["max_concurrent_tickets"])
    selected = ordered[-(capacity + 1):]
    selected_ids = {ticket["ticket_id"] for ticket in selected}

    for ticket in selected:
        ticket["assigned_agent_id"] = agent["agent_id"]
        ticket["status"] = "in_progress"
        ticket["resolved_at"] = None
        ticket["closed_at"] = None

    # An active ticket must not have a resolution record.
    if "resolutions" in transactions:
        transactions["resolutions"] = [
            r for r in transactions["resolutions"]
            if r["ticket_id"] not in selected_ids
        ]

    # Keep assignment history consistent with the modified assignments.
    for event in transactions["assignment_events"]:
        if (
            event["ticket_id"] in selected_ids
            and event["event_type"] == "assign"
        ):
            event["to_agent_id"] = agent["agent_id"]

    label(
        selected[-1],
        "agent_over_capacity",
        f"Agent exceeds concurrent capacity of {capacity}.",
    )
    used.update(selected_ids)

    # ------------------------------------------------------------------
    # 2. SLA ignores channel calendar
    # Find a ticket created outside the channel's business hours.
    # ------------------------------------------------------------------
    sla_ticket = None

    for candidate in ordered:
        if candidate["ticket_id"] in used:
            continue

        created = datetime.fromisoformat(candidate["created_at"])
        channel_id = int(candidate["channel_id"])

        # Channel 1 (email) and 3 (phone): weekdays 09:00-17:00,
        # Saturday 09:00-13:00. Other channels operate 24 hours.
        if channel_id not in (1, 3):
            continue

        weekday = created.weekday()
        outside_business_hours = (
            weekday == 6
            or (weekday == 5 and created.hour >= 13)
            or (weekday < 5 and (created.hour < 9 or created.hour >= 17))
        )

        if outside_business_hours:
            sla_ticket = candidate
            break

    if sla_ticket is None:
        raise ValueError(
            "Could not find a ticket created outside channel business hours."
        )

    created = datetime.fromisoformat(sla_ticket["created_at"])

    # Wrong calculation: plain elapsed time instead of the business calendar.
    incorrect_deadline = (created + timedelta(minutes=60)).isoformat()

    updated_sla_event = False

    for event in transactions["sla_events"]:
        if event["ticket_id"] == sla_ticket["ticket_id"]:
            if event["event_type"] == "created":
                event["target_at"] = incorrect_deadline
                event["details"] = (
                    "ANOMALY: elapsed-time SLA ignores channel calendar."
                )
                updated_sla_event = True
                break

    if not updated_sla_event:
        raise ValueError(
            "No created SLA event found for the selected SLA anomaly ticket."
        )

    label(
        sla_ticket,
        "sla_ignores_channel_calendar",
        "SLA deadline does not account for channel business hours.",
    )

    # ------------------------------------------------------------------
    # 3. Reopened ticket loses history
    # ------------------------------------------------------------------
    ticket = next(t for t in ordered if t["ticket_id"] not in used)

    ticket["status"] = "reopened"
    ticket["reopened_count"] = 1
    ticket["closed_at"] = None

    # Deliberately remove lifecycle history to create the anomaly.
    transactions["ticket_events"] = [
        event
        for event in transactions["ticket_events"]
        if event["ticket_id"] != ticket["ticket_id"]
    ]

    label(
        ticket,
        "reopened_ticket_loses_history",
        "Reopened ticket has lost its previous lifecycle events.",
    )

    # ------------------------------------------------------------------
    # 4. Transfer loop between two agents
    # ------------------------------------------------------------------
    ticket = next(t for t in ordered if t["ticket_id"] not in used)

    agent_a = agents[0]["agent_id"]
    agent_b = agents[1]["agent_id"]
    number = ticket["ticket_id"][-6:]

    transfers = [
        (agent_a, agent_b),
        (agent_b, agent_a),
        (agent_a, agent_b),
    ]

    for index, (source, destination) in enumerate(transfers, start=2):
        transactions["assignment_events"].append({
            "assignment_event_id": f"ASN-{number}-{index:03d}",
            "ticket_id": ticket["ticket_id"],
            "from_agent_id": source,
            "to_agent_id": destination,
            "from_queue_id": ticket["queue_id"],
            "to_queue_id": ticket["queue_id"],
            "assigned_at": ticket["created_at"],
            "assignment_reason": "ANOMALY: repeated transfer loop",
            "routing_score": 50.0,
            "event_type": "transfer",
        })

    # Final assignment matches the last transfer destination.
    ticket["assigned_agent_id"] = agent_b

    label(
        ticket,
        "transfer_loop",
        "Ticket repeatedly transfers between the same two agents.",
    )

    # ------------------------------------------------------------------
    # 5. Safety priority contradicts safety rule
    # ------------------------------------------------------------------
    safety_intents = [
        item for item in intents if int(item["is_safety_related"]) == 1
    ]

    if not safety_intents:
        raise ValueError("No safety-related intent found.")

    ticket = next(t for t in ordered if t["ticket_id"] not in used)

    ticket["intent_id"] = safety_intents[0]["intent_id"]
    ticket["priority"] = "Low"

    label(
        ticket,
        "priority_contradicts_safety_rule",
        "Safety-related ticket has Low priority instead of Critical.",
    )

    # Confirm that all five scenarios were labelled.
    expected_scenarios = {
        "agent_over_capacity",
        "sla_ignores_channel_calendar",
        "reopened_ticket_loses_history",
        "transfer_loop",
        "priority_contradicts_safety_rule",
    }

    actual_scenarios = {item["scenario_name"] for item in labels}

    if actual_scenarios != expected_scenarios:
        raise ValueError("Anomaly scenario labels are incomplete.")

    transactions["anomaly_labels"] = labels

    return transactions