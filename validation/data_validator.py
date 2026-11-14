from collections import Counter


def validate_dataset(master_data, transactions):
    """Validate generated master data, transactions and anomaly labels."""

    errors = []
    summary = {}

    required_tables = [
        "customers",
        "agents",
        "channels",
        "languages",
        "intents",
        "skills",
        "queues",
    ]

    for name in required_tables:
        if name not in master_data:
            errors.append(f"Missing master data: {name}")

    required_transactions = [
        "tickets",
        "messages",
        "assignment_events",
        "sla_events",
        "ticket_events",
        "resolutions",
    ]

    for name in required_transactions:
        if name not in transactions:
            errors.append(f"Missing transaction data: {name}")

    if errors:
        return {"valid": False, "errors": errors, "summary": summary}

    for name, records in master_data.items():
        summary[name] = len(records)

    for name, records in transactions.items():
        summary[name] = len(records)

    ticket_ids = {
        ticket["ticket_id"] for ticket in transactions["tickets"]
    }

    customer_ids = {
        customer["customer_id"] for customer in master_data["customers"]
    }

    agent_ids = {
        agent["agent_id"] for agent in master_data["agents"]
    }

    intent_ids = {
        intent["intent_id"] for intent in master_data["intents"]
    }

    for ticket in transactions["tickets"]:
        if ticket["customer_id"] not in customer_ids:
            errors.append(f"Unknown customer in {ticket['ticket_id']}")

        if ticket["intent_id"] not in intent_ids:
            errors.append(f"Unknown intent in {ticket['ticket_id']}")

        if ticket["assigned_agent_id"] not in agent_ids:
            errors.append(f"Unknown agent in {ticket['ticket_id']}")

        if ticket["priority"] not in [
            "Critical", "High", "Medium", "Low"
        ]:
            errors.append(f"Invalid priority in {ticket['ticket_id']}")

        if ticket["status"] == "reopened" and ticket["reopened_count"] < 1:
            errors.append(f"Invalid reopened count: {ticket['ticket_id']}")

    for name in [
        "messages",
        "assignment_events",
        "sla_events",
        "ticket_events",
        "resolutions",
    ]:
        for record in transactions[name]:
            if record["ticket_id"] not in ticket_ids:
                errors.append(
                    f"Unknown ticket reference in {name}: "
                    f"{record['ticket_id']}"
                )

    labels = transactions.get("anomaly_labels", [])
    scenario_counts = Counter(
        label["scenario_name"] for label in labels
    )

    expected_scenarios = {
        "agent_over_capacity",
        "sla_ignores_channel_calendar",
        "reopened_ticket_loses_history",
        "transfer_loop",
        "priority_contradicts_safety_rule",
    }

    if set(scenario_counts) != expected_scenarios:
        errors.append("Anomaly scenarios do not match the five required scenarios.")

    if len(labels) != 5:
        errors.append(f"Expected 5 anomaly labels, found {len(labels)}.")

    label_ticket_ids = [label["ticket_id"] for label in labels]

    if len(label_ticket_ids) != len(set(label_ticket_ids)):
        errors.append("Multiple anomaly labels use the same ticket.")

    if errors:
        return {"valid": False, "errors": errors, "summary": summary}

    return {"valid": True, "errors": [], "summary": summary}
