
from data.database import (
    initialize_database,
    get_table_names,
    check_foreign_keys,
)


def main() -> None:
    print("Initializing Customer Support Ticket Routing database...")

    database_path = initialize_database()

    print(f"\nDatabase created: {database_path}")
    print("\nTables created:")

    tables = get_table_names()
    for table in tables:
        print(f"  [OK] {table}")

    violations = check_foreign_keys()

    if violations:
        print("\nForeign-key violations found:")
        for violation in violations:
            print(tuple(violation))
        raise SystemExit(1)

    print(f"\nTotal tables: {len(tables)}")
    print("Foreign-key check: PASSED")
    print("Database initialization completed successfully.")


if __name__ == "__main__":
    main()
