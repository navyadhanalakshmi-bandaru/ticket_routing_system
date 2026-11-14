import random
import sqlite3

from config.settings import (
    RANDOM_SEED,
    OUTPUT_DIR,
    create_output_directories,
)
from data.database import initialize_database, get_connection
from generator import master_data as master_module
from generator import transactions as transaction_module
from generator.anomalies import inject_anomalies
from generator.export import export_dataset
from validation.data_validator import validate_dataset
from validation.reproducibility import (
    dataset_checksum,
    compare_datasets,
)


def prepare_random_seeds():
    """Reset random generators so each run starts from the same seed."""
    random.seed(RANDOM_SEED)
    master_module.random.seed(RANDOM_SEED)
    master_module.fake.seed_instance(RANDOM_SEED)
    transaction_module.rng.seed(RANDOM_SEED + 1)


def build_supporting_data(master_data):
    """Build relationship and configuration records for the database."""

    rng = random.Random(RANDOM_SEED + 2)

    agents = master_data["agents"]
    channels = master_data["channels"]
    languages = master_data["languages"]
    intents = master_data["intents"]
    skills = master_data["skills"]
    queues = master_data["queues"]

    skill_ids = {
        s["skill_name"]: s["skill_id"]
        for s in skills
    }
    intent_ids = {
        i["intent_name"]: i["intent_id"]
        for i in intents
    }
    queue_ids = {
        q["queue_name"]: q["queue_id"]
        for q in queues
    }

    # Map each ticket intent to its required skills.
    skill_intent_map = {
        "Billing": [
            "Billing Support",
            "Customer Communication",
        ],
        "Technical Support": [
            "Technical Troubleshooting",
            "Customer Communication",
        ],
        "Account Access": [
            "Account Management",
            "Customer Communication",
        ],
        "Refund": [
            "Refund Processing",
            "Billing Support",
        ],
        "Delivery": [
            "Delivery Support",
            "Customer Communication",
        ],
        "Cancellation": [
            "Account Management",
            "Customer Communication",
        ],
        "Product Information": [
            "Product Knowledge",
        ],
        "Security Incident": [
            "Security Investigation",
            "Account Management",
        ],
        "Fraud Report": [
            "Security Investigation",
            "Billing Support",
        ],
    }

    skill_intents = []

    for intent_name, skill_names in skill_intent_map.items():
        for skill_name in skill_names:
            skill_intents.append({
                "skill_id": skill_ids[skill_name],
                "intent_id": intent_ids[intent_name],
                "is_required": 1,
            })

    # Map ticket intents to their queues.
    queue_intent_map = {
        "General Support": [
            "Product Information",
            "Cancellation",
            "Account Access",
        ],
        "Billing Support": [
            "Billing",
            "Refund",
        ],
        "Technical Support": [
            "Technical Support",
        ],
        "Account Security": [
            "Security Incident",
            "Fraud Report",
        ],
        "Delivery Support": [
            "Delivery",
        ],
        "Priority Escalation": [
            "Security Incident",
            "Fraud Report",
            "Technical Support",
        ],
    }

    queue_intents = []

    for queue_name, intent_names in queue_intent_map.items():
        for intent_name in intent_names:
            queue_intents.append({
                "queue_id": queue_ids[queue_name],
                "intent_id": intent_ids[intent_name],
            })

    # ---------------------------------------------------------
    # AGENT SKILLS
    # First 20 agents are cross-trained.
    # Remaining agents receive four specialized skills.
    # Required skill proficiency is always at least 3.
    # ---------------------------------------------------------

    agent_skills = []

    CROSS_TRAINED_AGENTS = 20

    for index, agent in enumerate(agents):
        if index < CROSS_TRAINED_AGENTS:
            selected_skills = skills.copy()
        else:
            selected_skills = rng.sample(skills, k=4)

        for skill in selected_skills:
            agent_skills.append({
                "agent_id": agent["agent_id"],
                "skill_id": skill["skill_id"],
                "proficiency": rng.randint(3, 5),
            })

    agent_skill_pairs = [
        (record["agent_id"], record["skill_id"])
        for record in agent_skills
    ]

    if len(agent_skill_pairs) != len(set(agent_skill_pairs)):
        raise ValueError(
            "Duplicate agent-skill combinations detected."
        )

    # ---------------------------------------------------------
    # AGENT LANGUAGES
    # First 20 agents support every configured language.
    # Remaining agents support English and two other languages.
    # Non-English language proficiency is at least 3.
    # ---------------------------------------------------------

    english_id = next(
        lang["language_id"]
        for lang in languages
        if lang["language_code"] == "en"
    )

    all_language_ids = [
        lang["language_id"]
        for lang in languages
    ]

    other_languages = [
        language_id
        for language_id in all_language_ids
        if language_id != english_id
    ]

    agent_languages = []

    for index, agent in enumerate(agents):
        if index < CROSS_TRAINED_AGENTS:
            selected_language_ids = all_language_ids.copy()
        else:
            selected_language_ids = [english_id]
            selected_language_ids.extend(
                rng.sample(other_languages, k=2)
            )

        for language_id in sorted(selected_language_ids):
            agent_languages.append({
                "agent_id": agent["agent_id"],
                "language_id": language_id,
                "proficiency": (
                    5 if language_id == english_id
                    else rng.randint(3, 5)
                ),
            })

    # ---------------------------------------------------------
    # AGENT SHIFTS
    # Everyone works Monday-Friday.
    # Every 2nd agent also works Saturday (email/phone Saturday hours).
    # Every 4th agent also works Sunday (24/7 chat coverage).
    # No random numbers are used, so other data is unaffected.
    # ---------------------------------------------------------

    agent_shifts = []

    for index, agent in enumerate(agents, start=1):
        start_hour = 8 + (index % 3)

        working_days = list(range(5))

        if index % 2 == 0:
            working_days.append(5)

        if index % 4 == 0:
            working_days.append(6)

        for day in working_days:
            agent_shifts.append({
                "agent_id": agent["agent_id"],
                "day_of_week": day,
                "start_time": f"{start_hour:02d}:00",
                "end_time": f"{start_hour + 8:02d}:00",
                "timezone": agent["timezone"],
            })

    # ---------------------------------------------------------
    # BUSINESS AND CHANNEL CALENDARS
    # ---------------------------------------------------------

    calendar_records = []
    channel_calendar_records = []

    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
    ]

    for channel in channels:
        channel_name = channel["channel_name"]
        calendar_id = channel["channel_id"]

        calendar = {
            "calendar_id": calendar_id,
            "calendar_name": f"{channel_name.title()} Calendar",
            "timezone": "Asia/Kolkata",
        }

        for day in weekdays:
            if channel_name in ("chat", "web"):
                calendar[f"{day}_open"] = "00:00"
                calendar[f"{day}_close"] = "23:59"
            else:
                calendar[f"{day}_open"] = "09:00"
                calendar[f"{day}_close"] = "17:00"

        for day in ["saturday", "sunday"]:
            if channel_name in ("chat", "web"):
                calendar[f"{day}_open"] = "00:00"
                calendar[f"{day}_close"] = "23:59"
            elif day == "saturday":
                calendar[f"{day}_open"] = "09:00"
                calendar[f"{day}_close"] = "13:00"
            else:
                calendar[f"{day}_open"] = None
                calendar[f"{day}_close"] = None

        calendar_records.append(calendar)

        channel_calendar_records.append({
            "channel_id": channel["channel_id"],
            "calendar_id": calendar_id,
        })

    # ---------------------------------------------------------
    # SLA POLICIES
    # ---------------------------------------------------------

    response_minutes = {
        "Critical": 5,
        "High": 15,
        "Medium": 60,
        "Low": 240,
    }

    resolution_minutes = {
        "Critical": 60,
        "High": 240,
        "Medium": 1440,
        "Low": 4320,
    }

    sla_policies = []
    policy_id = 1

    for channel in channels:
        for priority in ["Critical", "High", "Medium", "Low"]:
            sla_policies.append({
                "sla_policy_id": policy_id,
                "policy_name": (
                    f"{priority} {channel['channel_name']} SLA"
                ),
                "priority": priority,
                "channel_id": channel["channel_id"],
                "response_minutes": response_minutes[priority],
                "resolution_minutes": resolution_minutes[priority],
                "calendar_id": channel["channel_id"],
                "is_active": 1,
            })

            policy_id += 1

    # ---------------------------------------------------------
    # PRIORITY RULES AND SAFETY FLOORS
    # ---------------------------------------------------------

    priority_rules = []

    for intent in intents:
        safety = int(intent["is_safety_related"]) == 1

        priority_rules.append({
            "priority_rule_id": intent["intent_id"],
            "rule_name": f"{intent['intent_name']} default rule",
            "intent_id": intent["intent_id"],
            "customer_tier": None,
            "channel_id": None,
            "priority": intent["default_priority"],
            "priority_floor": "Critical" if safety else None,
            "rule_order": 1,
            "is_active": 1,
        })

    return {
        "agent_skills": agent_skills,
        "agent_languages": agent_languages,
        "skill_intents": skill_intents,
        "queue_intents": queue_intents,
        "agent_shifts": agent_shifts,
        "business_calendars": calendar_records,
        "channel_calendars": channel_calendar_records,
        "calendar_holidays": [],
        "sla_policies": sla_policies,
        "priority_rules": priority_rules,
    }


def insert_records(connection, table_name, records):
    """Insert a list of dictionaries into a database table."""

    if not records:
        return

    columns = list(records[0].keys())
    column_sql = ", ".join(columns)
    placeholder_sql = ", ".join(["?"] * len(columns))

    sql = (
        f"INSERT INTO {table_name} "
        f"({column_sql}) VALUES ({placeholder_sql})"
    )

    values = [
        tuple(record[column] for column in columns)
        for record in records
    ]

    try:
        connection.executemany(sql, values)
    except sqlite3.IntegrityError as error:
        raise sqlite3.IntegrityError(
            f"Failed inserting into table '{table_name}': {error}"
        ) from error


def save_to_database(
    master_data,
    supporting_data,
    transactions,
    db_path,
):
    """Insert all records in foreign-key-safe order."""

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        for table in [
            "channels",
            "languages",
            "intents",
            "skills",
            "queues",
            "customers",
            "agents",
        ]:
            insert_records(
                connection,
                table,
                master_data[table],
            )

        for table in [
            "priority_rules",
            "agent_skills",
            "agent_languages",
            "skill_intents",
            "queue_intents",
            "business_calendars",
            "channel_calendars",
            "calendar_holidays",
            "agent_shifts",
            "sla_policies",
        ]:
            insert_records(
                connection,
                table,
                supporting_data[table],
            )

        insert_records(
            connection,
            "tickets",
            transactions["tickets"],
        )

        for table in [
            "messages",
            "assignment_events",
            "sla_events",
            "ticket_events",
            "resolutions",
            "anomaly_labels",
        ]:
            insert_records(
                connection,
                table,
                transactions.get(table, []),
            )

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                f"Foreign-key violations detected: {violations[:5]}"
            )


def generate_dataset():
    """Generate and validate one deterministic dataset."""

    prepare_random_seeds()

    master_data = master_module.generate_master_data()

    transactions = transaction_module.generate_transactions(
        master_data
    )

    print("Injecting five labelled anomaly scenarios...")

    transactions = inject_anomalies(
        transactions,
        master_data,
    )

    validation = validate_dataset(
        master_data,
        transactions,
    )

    if not validation["valid"]:
        print("\nDataset validation FAILED:")

        for error in validation["errors"]:
            print(f"  - {error}")

        raise ValueError("Generated dataset failed validation.")

    print("Dataset validation: PASSED")

    supporting_data = build_supporting_data(master_data)

    return master_data, supporting_data, transactions


def main():
    print("Starting synthetic dataset generation...")

    create_output_directories()

    # First reproducibility run.
    print("\n========== REPRODUCIBILITY RUN 1 ==========")

    master1, supporting1, transactions1 = generate_dataset()

    first_data = {
        "master_data": master1,
        "supporting_data": supporting1,
        "transactions": transactions1,
    }

    checksum1 = dataset_checksum(first_data)

    print("Run 1 checksum:", checksum1)

    del first_data
    del master1, supporting1, transactions1

    # Second reproducibility run.
    print("\n========== REPRODUCIBILITY RUN 2 ==========")

    master_data, supporting_data, transactions = generate_dataset()

    second_data = {
        "master_data": master_data,
        "supporting_data": supporting_data,
        "transactions": transactions,
    }

    checksum2 = dataset_checksum(second_data)

    print("Run 2 checksum:", checksum2)

    comparison = compare_datasets(
        {"checksum": checksum1},
        {"checksum": checksum2},
    )

    print("\n========== REPRODUCIBILITY RESULT ==========")

    if not comparison["reproducible"]:
        print("FAILED: Generated datasets are different.")
        raise SystemExit(1)

    print("PASSED: Both generated datasets are identical.")

    # Save only after reproducibility succeeds.
    db_path = OUTPUT_DIR / "ticket_routing_generated.db"

    if db_path.exists():
        raise FileExistsError(
            f"\n{db_path} already exists. "
            "Delete only this generated database before running again. "
            "Your original ticket_routing.db is not affected."
        )

    print("\nSaving records to SQLite...")

    save_to_database(
        master_data,
        supporting_data,
        transactions,
        db_path,
    )

    print("Exporting CSV and JSON files...")

    exported_counts = export_dataset(transactions)

    print("\nGeneration completed.")
    print(f"Generated database: {db_path}")

    print("\nRecord counts:")

    for name, records in master_data.items():
        print(f"  {name}: {len(records)}")

    for name, records in supporting_data.items():
        print(f"  {name}: {len(records)}")

    for name, records in transactions.items():
        print(f"  {name}: {len(records)}")

    print("\nExport counts:")

    for name, count in exported_counts.items():
        print(f"  {name}: {count}")

    print("\nFinal dataset checksum:")
    print(checksum2)

    print("\nSQLite database and exports created successfully.")


if __name__ == "__main__":
    main()