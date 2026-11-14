import csv
import json
from pathlib import Path

from config.settings import (
    CSV_DIR,
    JSON_DIR,
    GROUND_TRUTH_DIR,
    create_output_directories,
)


def export_dataset(transactions):
    """Export transaction data and keep anomaly labels separate."""
    create_output_directories()

    exported_counts = {}

    for table_name, records in transactions.items():
        if table_name == "anomaly_labels":
            continue

        if not records:
            continue

        csv_path = CSV_DIR / f"{table_name}.csv"
        json_path = JSON_DIR / f"{table_name}.json"

        fieldnames = list(records[0].keys())

        with csv_path.open(
            "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(records)

        with json_path.open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(
                records,
                file,
                indent=2,
                ensure_ascii=False,
            )

        exported_counts[table_name] = len(records)

    # Ground truth is deliberately stored outside normal input exports.
    labels = transactions.get("anomaly_labels", [])

    ground_truth_csv = GROUND_TRUTH_DIR / "ground_truth.csv"
    ground_truth_json = GROUND_TRUTH_DIR / "ground_truth.json"

    ground_truth_fields = [
        "anomaly_id",
        "ticket_id",
        "scenario_name",
        "expected_issue",
    ]

    with ground_truth_csv.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=ground_truth_fields,
        )
        writer.writeheader()
        writer.writerows(labels)

    with ground_truth_json.open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(
            labels,
            file,
            indent=2,
            ensure_ascii=False,
        )

    exported_counts["anomaly_labels"] = len(labels)

    return exported_counts
