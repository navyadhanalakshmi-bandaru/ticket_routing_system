
import sqlite3

from data.database import (
    initialize_database,
    get_connection,
    get_table_names,
    check_foreign_keys,
)


def test_database_creates_tables(tmp_path):
    db_path = tmp_path / "test_database.db"

    initialize_database(db_path)
    tables = get_table_names(db_path)

    required_tables = {
        "customers",
        "channels",
        "tickets",
        "messages",
        "intents",
        "languages",
        "priority_rules",
        "agents",
        "skills",
        "queues",
        "assignment_events",
        "sla_events",
        "resolutions",
        "agent_skills",
        "agent_languages",
        "skill_intents",
        "queue_intents",
        "ticket_events",
        "business_calendars",
        "channel_calendars",
        "calendar_holidays",
        "agent_shifts",
        "sla_policies",
        "anomaly_labels",
    }

    assert required_tables.issubset(set(tables))


def test_foreign_keys_are_enabled(tmp_path):
    db_path = tmp_path / "test_foreign_keys.db"

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        result = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

    assert result == 1


def test_foreign_key_violations_are_empty(tmp_path):
    db_path = tmp_path / "test_integrity.db"

    initialize_database(db_path)

    assert check_foreign_keys(db_path) == []


def test_invalid_customer_reference_is_rejected(tmp_path):
    db_path = tmp_path / "test_invalid_reference.db"

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO channels (channel_id, channel_name)
            VALUES (1, 'email')
            """
        )
        connection.execute(
            """
            INSERT INTO languages (
                language_id, language_code, language_name
            )
            VALUES (1, 'en', 'English')
            """
        )
        connection.execute(
            """
            INSERT INTO intents (intent_id, intent_name)
            VALUES (1, 'Billing')
            """
        )

        try:
            connection.execute(
                """
                INSERT INTO tickets (
                    ticket_id, customer_id, channel_id,
                    intent_id, language_id, subject, priority,
                    created_at
                )
                VALUES (
                    'TKT-TEST-000001', 'UNKNOWN-CUSTOMER',
                    1, 1, 1, 'Test ticket', 'Low',
                    '2026-11-14T10:00:00'
                )
                """
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError(
                "Database accepted a ticket with an invalid customer."
            )
