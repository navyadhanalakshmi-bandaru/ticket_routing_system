
from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"

CSV_DIR = OUTPUT_DIR / "csv"
JSON_DIR = OUTPUT_DIR / "json"
GROUND_TRUTH_DIR = OUTPUT_DIR / "ground_truth"
REPORT_DIR = OUTPUT_DIR / "reports"

# Reproducibility
RANDOM_SEED = 20261022

# Dataset size
NUM_CUSTOMERS = 10000
NUM_AGENTS = 100
NUM_TICKETS = 30000
NUM_MESSAGES = 100000
NUM_EVENT_DAYS = 90

# Time range
START_DATE = "2026-08-17"
END_DATE = "2026-11-14"

# Database
DATABASE_PATH = PROJECT_ROOT / "ticket_routing.db"

# Anomaly scenarios
ANOMALY_SCENARIOS = [
    "agent_over_capacity",
    "sla_ignores_channel_calendar",
    "reopened_ticket_loses_history",
    "transfer_loop",
    "priority_contradicts_safety_rule",
]

def create_output_directories():
    """Create all output directories if they do not exist."""
    for directory in [
        CSV_DIR,
        JSON_DIR,
        GROUND_TRUTH_DIR,
        REPORT_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
