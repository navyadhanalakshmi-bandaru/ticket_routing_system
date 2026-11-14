
import sqlite3
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "ticket_routing.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection(
    db_path: Optional[str | Path] = None,
) -> sqlite3.Connection:
    """Open a SQLite connection with foreign-key enforcement enabled."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(
    db_path: Optional[str | Path] = None,
) -> Path:
    """Create all tables and indexes defined in schema.sql."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection(db_path) as connection:
        connection.executescript(schema)

    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    return path


def get_table_names(
    db_path: Optional[str | Path] = None,
) -> list[str]:
    """Return all user-created table names."""
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

    return [row["name"] for row in rows]


def check_foreign_keys(
    db_path: Optional[str | Path] = None,
) -> list[sqlite3.Row]:
    """Return any foreign-key violations."""
    with get_connection(db_path) as connection:
        return connection.execute("PRAGMA foreign_key_check").fetchall()
