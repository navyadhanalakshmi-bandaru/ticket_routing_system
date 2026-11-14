import hashlib
import json


def dataset_checksum(data):
    """Calculate a deterministic SHA-256 checksum for generated data."""

    serialized = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(serialized).hexdigest()


def compare_datasets(first, second):
    """Compare two generated datasets using their checksums."""

    first_checksum = dataset_checksum(first)
    second_checksum = dataset_checksum(second)

    return {
        "reproducible": first_checksum == second_checksum,
        "first_checksum": first_checksum,
        "second_checksum": second_checksum,
    }
