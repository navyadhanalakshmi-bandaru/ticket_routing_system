"""Makes ticket status depend on ticket age (deterministic, own RNG).

Rule: only tickets created within the last `window_hours` may stay active, and
the number of active tickets is capped at `max_active_ratio` x total agent capacity.
Every other active ticket is converted to resolved/closed with a resolution record.
"""
import random
from datetime import datetime, timedelta

ACTIVE = {"assigned", "in_progress", "pending_customer", "queued", "reopened"}


def normalize_workload(transactions, master_data, end_date, seed,
                       window_hours=24, max_active_ratio=0.5):
    rng = random.Random(seed + 7)
    end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
    cutoff = end - timedelta(hours=window_hours)
    capacity = sum(int(a["max_concurrent_tickets"]) for a in master_data["agents"])
    budget = int(capacity * max_active_ratio)

    resolutions = transactions["resolutions"]
    template = resolutions[0]
    kept, converted = 0, 0

    newest_first = sorted(transactions["tickets"],
                          key=lambda t: (t["created_at"], t["ticket_id"]), reverse=True)
    for t in newest_first:
        if t["status"] not in ACTIVE:
            continue
        if datetime.fromisoformat(t["created_at"]) >= cutoff and kept < budget:
            kept += 1
            continue

        first_response = datetime.fromisoformat(t["first_response_at"])
        resolved = min(end, first_response + timedelta(minutes=rng.randint(10, 1440)))
        t["status"] = "closed" if rng.random() < 0.25 else "resolved"
        t["resolved_at"] = resolved.isoformat()
        t["closed_at"] = None
        if t["status"] == "closed":
            t["closed_at"] = min(end, resolved + timedelta(minutes=rng.randint(5, 120))).isoformat()

        new = dict(template)  # copy an existing record so every column is present
        new["resolution_id"] = f"RES-{t['ticket_id'][-6:]}-001"
        new["ticket_id"] = t["ticket_id"]
        new["resolved_at"] = t["resolved_at"]
        if "csat_score" in new:
            new["csat_score"] = rng.randint(1, 5)
        for key in ("resolved_by_agent_id", "agent_id"):
            if key in new:
                new[key] = t.get("assigned_agent_id")
        resolutions.append(new)
        converted += 1

    print(f"Workload normalised: kept {kept} active (budget {budget}), converted {converted}.")
    return transactions