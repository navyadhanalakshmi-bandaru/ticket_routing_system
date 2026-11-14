
import random
from datetime import datetime, timedelta

from config.settings import (
    RANDOM_SEED,
    NUM_TICKETS,
    NUM_MESSAGES,
    START_DATE,
    END_DATE,
)

from generator.master_data import (
    CHANNELS,
    LANGUAGES,
    INTENTS,
    QUEUES,
)

rng = random.Random(RANDOM_SEED + 1)

START = datetime.fromisoformat(START_DATE)

END = datetime.fromisoformat(END_DATE).replace(
    hour=23,
    minute=59,
    second=59,
)


SUBJECTS = [
    "Payment issue",
    "Unable to access account",
    "Order not delivered",
    "Refund request",
    "Technical problem",
    "Account security concern",
    "Product information request",
    "Subscription cancellation",
]

MESSAGE_TEXTS = [
    "I need help with this issue.",
    "Could you please check my request?",
    "Thank you for your assistance.",
    "I am still experiencing the problem.",
    "Please provide an update.",
    "The issue has been resolved.",
    "I would like to request further information.",
]

RESOLUTION_CATEGORIES = [
    "Information Provided",
    "Issue Fixed",
    "Refund Processed",
    "Account Restored",
    "Technical Resolution",
]


def random_datetime():
    """Generate a timestamp inside the configured date range."""

    seconds = int((END - START).total_seconds())

    return START + timedelta(
        seconds=rng.randint(0, seconds)
    )


def safe_datetime_add(base_datetime, minutes):
    """Add minutes without exceeding the configured end date."""

    return min(
        base_datetime + timedelta(minutes=minutes),
        END,
    )


def distribute_messages():
    """Distribute exactly NUM_MESSAGES messages across tickets."""

    if NUM_MESSAGES < NUM_TICKETS:
        raise ValueError(
            "NUM_MESSAGES must be at least NUM_TICKETS."
        )

    counts = [1] * NUM_TICKETS

    remaining = NUM_MESSAGES - NUM_TICKETS

    for _ in range(remaining):
        counts[rng.randrange(NUM_TICKETS)] += 1

    return counts


def generate_transactions(master_data):
    """Generate deterministic ticket and transaction records."""

    # Reset RNG on every invocation for reproducibility.
    rng.seed(RANDOM_SEED + 1)

    customers = master_data["customers"]
    agents = master_data["agents"]

    customer_ids = [
        customer["customer_id"]
        for customer in customers
    ]

    agent_ids = [
        agent["agent_id"]
        for agent in agents
    ]

    intent_lookup = {
        item[0]: index
        for index, item in enumerate(INTENTS, 1)
    }

    channel_ids = list(range(1, len(CHANNELS) + 1))
    language_ids = list(range(1, len(LANGUAGES) + 1))
    queue_ids = list(range(1, len(QUEUES) + 1))

    message_counts = distribute_messages()

    result = {
        "tickets": [],
        "messages": [],
        "assignment_events": [],
        "sla_events": [],
        "ticket_events": [],
        "resolutions": [],
    }

    for i in range(1, NUM_TICKETS + 1):

        ticket_id = f"TKT-2026-{i:06d}"

        customer_id = rng.choice(customer_ids)
        channel_id = rng.choice(channel_ids)
        language_id = rng.choice(language_ids)

        intent_name, _, default_priority, is_safety = (
            rng.choice(INTENTS)
        )

        intent_id = intent_lookup[intent_name]

        # Safety-related tickets must always have Critical priority.
        if is_safety:
            priority = "Critical"
        else:
            priority = rng.choices(
                ["Critical", "High", "Medium", "Low"],
                weights=[3, 17, 50, 30],
            )[0]

        queue_id = rng.choice(queue_ids)
        agent_id = rng.choice(agent_ids)

        created_at = random_datetime()

        # First response must remain within the configured period.
        first_response_at = safe_datetime_add(
            created_at,
            rng.randint(1, 180),
        )

        status = rng.choices(
            [
                "resolved",
                "closed",
                "in_progress",
                "pending_customer",
                "queued",
            ],
            weights=[45, 15, 20, 10, 10],
        )[0]

        resolved_at = None
        closed_at = None

        if status in ("resolved", "closed"):

            resolved_datetime = safe_datetime_add(
                first_response_at,
                rng.randint(10, 1440),
            )

            resolved_at = resolved_datetime.isoformat()

        if status == "closed":

            closed_datetime = safe_datetime_add(
                datetime.fromisoformat(resolved_at),
                rng.randint(5, 120),
            )

            closed_at = closed_datetime.isoformat()

        first_response_value = first_response_at.isoformat()

        ticket = {
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "channel_id": channel_id,
            "intent_id": intent_id,
            "language_id": language_id,
            "queue_id": queue_id,
            "assigned_agent_id": agent_id,
            "subject": rng.choice(SUBJECTS),
            "description": (
                f"Customer request concerning "
                f"{intent_name.lower()}."
            ),
            "priority": priority,
            "status": status,
            "created_at": created_at.isoformat(),
            "first_response_at": first_response_value,
            "resolved_at": resolved_at,
            "closed_at": closed_at,
            "reopened_count": 0,
            "source_reference": f"SRC-{i:08d}",
        }

        result["tickets"].append(ticket)

        # Initial assignment event.
        result["assignment_events"].append({
            "assignment_event_id": f"ASN-{i:06d}-001",
            "ticket_id": ticket_id,
            "from_agent_id": None,
            "to_agent_id": agent_id,
            "from_queue_id": None,
            "to_queue_id": queue_id,
            "assigned_at": created_at.isoformat(),
            "assignment_reason": "Initial synthetic assignment",
            "routing_score": round(
                rng.uniform(60, 100), 2
            ),
            "event_type": "assign",
        })

        # Ticket lifecycle: creation.
        result["ticket_events"].append({
            "ticket_event_id": f"EVT-{i:06d}-001",
            "ticket_id": ticket_id,
            "event_type": "created",
            "old_status": None,
            "new_status": "open",
            "event_at": created_at.isoformat(),
            "actor_type": "system",
            "actor_id": None,
            "notes": "Ticket created",
        })

        # Ticket lifecycle: assignment.
        result["ticket_events"].append({
            "ticket_event_id": f"EVT-{i:06d}-002",
            "ticket_id": ticket_id,
            "event_type": "assigned",
            "old_status": "open",
            "new_status": "assigned",
            "event_at": created_at.isoformat(),
            "actor_type": "system",
            "actor_id": None,
            "notes": "Agent assigned",
        })

        # Initial response SLA.
        response_due = safe_datetime_add(
            created_at,
            60,
        )

        result["sla_events"].append({
            "sla_event_id": f"SLA-{i:06d}-001",
            "ticket_id": ticket_id,
            "event_type": "created",
            "target_at": response_due.isoformat(),
            "occurred_at": created_at.isoformat(),
            "is_breach": 0,
            "details": "Initial response SLA target",
        })

        result["sla_events"].append({
            "sla_event_id": f"SLA-{i:06d}-002",
            "ticket_id": ticket_id,
            "event_type": "response_met",
            "target_at": response_due.isoformat(),
            "occurred_at": first_response_value,
            "is_breach": int(
                first_response_at > response_due
            ),
            "details": "Synthetic first response",
        })

        # Resolution record.
        if resolved_at:

            result["resolutions"].append({
                "resolution_id": f"RES-{i:06d}-001",
                "ticket_id": ticket_id,
                "resolution_number": 1,
                "resolved_by_agent_id": agent_id,
                "resolution_category": rng.choice(
                    RESOLUTION_CATEGORIES
                ),
                "resolution_notes": "Synthetic resolution record",
                "resolved_at": resolved_at,
                "csat_score": rng.randint(1, 5),
                "customer_feedback": (
                    "Thank you for your support."
                ),
            })

        # Generate the exact allocated number of messages.
        count = message_counts[i - 1]

        for j in range(1, count + 1):

            sender_type = (
                "customer" if j % 2 == 1 else "agent"
            )

            sender_id = (
                customer_id
                if sender_type == "customer"
                else agent_id
            )

            sent_at = safe_datetime_add(
                created_at,
                j * rng.randint(1, 10),
            )

            result["messages"].append({
                "message_id": f"MSG-{i:06d}-{j:03d}",
                "ticket_id": ticket_id,
                "sender_type": sender_type,
                "sender_id": sender_id,
                "message_text": rng.choice(MESSAGE_TEXTS),
                "sent_at": sent_at.isoformat(),
                "is_internal": 0,
            })

    assert len(result["tickets"]) == NUM_TICKETS

    assert len(result["messages"]) == NUM_MESSAGES

    return result
