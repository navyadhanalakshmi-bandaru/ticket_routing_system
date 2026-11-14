import random
from datetime import datetime, timedelta

from faker import Faker

from config.settings import (
    RANDOM_SEED,
    NUM_CUSTOMERS,
    NUM_AGENTS,
    START_DATE,
    END_DATE,
)

fake = Faker()
random.seed(RANDOM_SEED)

# Fixed reference dates: never depend on the current system date.
REFERENCE_DATE = datetime.fromisoformat(END_DATE)
FIRST_TICKET_DATE = datetime.fromisoformat(START_DATE)

# Customers and agents must exist BEFORE the first ticket is created.
CUSTOMER_END_DATE = FIRST_TICKET_DATE - timedelta(days=1)
CUSTOMER_START_DATE = CUSTOMER_END_DATE - timedelta(days=730)
AGENT_END_DATE = FIRST_TICKET_DATE - timedelta(days=30)
AGENT_START_DATE = AGENT_END_DATE - timedelta(days=1795)

CHANNELS = ["email", "chat", "phone", "web"]

LANGUAGES = [
    ("en", "English"),
    ("hi", "Hindi"),
    ("te", "Telugu"),
    ("ta", "Tamil"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
]

INTENTS = [
    ("Billing", "Billing and payment questions", "Medium", 0),
    ("Technical Support", "Technical problems", "High", 0),
    ("Account Access", "Account access issues", "High", 0),
    ("Refund", "Refund requests", "Medium", 0),
    ("Delivery", "Delivery and shipment", "Medium", 0),
    ("Cancellation", "Cancellation requests", "Medium", 0),
    ("Product Information", "Product questions", "Low", 0),
    ("Security Incident", "Account security incidents", "Critical", 1),
    ("Fraud Report", "Suspected fraudulent activity", "Critical", 1),
]

SKILLS = [
    "Billing Support",
    "Technical Troubleshooting",
    "Account Management",
    "Refund Processing",
    "Delivery Support",
    "Security Investigation",
    "Customer Communication",
    "Product Knowledge",
]

QUEUES = [
    "General Support",
    "Billing Support",
    "Technical Support",
    "Account Security",
    "Delivery Support",
    "Priority Escalation",
]

TIERS = ["Standard", "Silver", "Gold", "Platinum"]

# Routing only accepts 'available' and 'busy', so most agents must be one of those.
AGENT_STATUSES = ["available", "busy", "away", "offline"]
AGENT_STATUS_WEIGHTS = [55, 30, 10, 5]


def generate_customers(rng=None):
    rng = rng or random.Random(RANDOM_SEED)
    customers = []

    for i in range(1, NUM_CUSTOMERS + 1):
        customers.append({
            "customer_id": f"CUS-{i:06d}",
            "customer_name": fake.name(),
            "email": f"customer{i}@example.com",
            "phone": fake.phone_number()[:30],
            "customer_tier": rng.choices(
                TIERS,
                weights=[60, 20, 15, 5],
            )[0],
            "created_at": fake.date_time_between(
                start_date=CUSTOMER_START_DATE,
                end_date=CUSTOMER_END_DATE,
            ).isoformat(),
            "country": fake.country(),
        })

    return customers


def generate_agents(rng=None):
    rng = rng or random.Random(RANDOM_SEED + 3)
    agents = []

    for i in range(1, NUM_AGENTS + 1):
        # Agents 1 and 2 are used by the over-capacity and transfer-loop
        # anomalies, so they must always be able to receive tickets.
        if i <= 2:
            status = "available"
            rng.choices(AGENT_STATUSES, weights=AGENT_STATUS_WEIGHTS)  # keep RNG sequence stable
        else:
            status = rng.choices(
                AGENT_STATUSES,
                weights=AGENT_STATUS_WEIGHTS,
            )[0]

        agents.append({
            "agent_id": f"AGT-{i:06d}",
            "agent_name": fake.name(),
            "email": f"agent{i}@example.com",
            "status": status,
            "max_concurrent_tickets": rng.randint(4, 8),
            "timezone": "Asia/Kolkata",
            "hire_date": fake.date_between(
                start_date=AGENT_START_DATE.date(),
                end_date=AGENT_END_DATE.date(),
            ).isoformat(),
            "is_active": 1,
        })

    return agents


def generate_master_data():
    # Reset every random source on each call so repeated runs are identical.
    random.seed(RANDOM_SEED)
    fake.seed_instance(RANDOM_SEED)

    customers = generate_customers(random.Random(RANDOM_SEED))
    agents = generate_agents(random.Random(RANDOM_SEED + 3))

    return {
        "customers": customers,
        "agents": agents,

        "channels": [
            {"channel_id": i, "channel_name": name}
            for i, name in enumerate(CHANNELS, 1)
        ],

        "languages": [
            {
                "language_id": i,
                "language_code": code,
                "language_name": name,
            }
            for i, (code, name) in enumerate(LANGUAGES, 1)
        ],

        "intents": [
            {
                "intent_id": i,
                "intent_name": name,
                "description": description,
                "default_priority": priority,
                "is_safety_related": safety,
            }
            for i, (name, description, priority, safety)
            in enumerate(INTENTS, 1)
        ],

        "skills": [
            {
                "skill_id": i,
                "skill_name": name,
                "description": f"Handles {name.lower()} cases",
            }
            for i, name in enumerate(SKILLS, 1)
        ],

        "queues": [
            {
                "queue_id": i,
                "queue_name": name,
                "description": f"Queue for {name.lower()}",
                "is_active": 1,
            }
            for i, name in enumerate(QUEUES, 1)
        ],
    }