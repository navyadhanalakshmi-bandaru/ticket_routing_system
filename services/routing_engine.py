
import sqlite3
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DB_PATH = (
    PROJECT_ROOT / "outputs" / "ticket_routing_generated.db"
)

DEFAULT_TIMEZONE = "Asia/Kolkata"

ACTIVE_STATUSES = (
    "assigned",
    "in_progress",
    "pending_customer",
    "reopened",
)

ROUTABLE_STATUSES = (
    "open",
    "queued",
    "reopened",
)

MIN_SKILL_PROFICIENCY = 3
MIN_LANGUAGE_PROFICIENCY = 3

WEIGHTS = {
    "skill": 0.30,
    "language": 0.25,
    "availability": 0.20,
    "capacity": 0.15,
    "workload": 0.10,
}


def parse_routing_datetime(value):
    """Convert a timestamp into a timezone-aware datetime."""
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(value)

    if result.tzinfo is None:
        result = result.replace(
            tzinfo=ZoneInfo(DEFAULT_TIMEZONE)
        )

    return result


def is_agent_on_shift(agent, shifts, routing_time):
    """Check whether an agent is working at the routing time."""
    timezone_name = agent["timezone"] or DEFAULT_TIMEZONE

    try:
        local_time = routing_time.astimezone(
            ZoneInfo(timezone_name)
        )
    except (ZoneInfoNotFoundError, ValueError):
        return False

    weekday = local_time.weekday()
    current_time = local_time.time().replace(tzinfo=None)

    for shift in shifts:
        if shift["day_of_week"] != weekday:
            continue

        start = time.fromisoformat(shift["start_time"])
        end = time.fromisoformat(shift["end_time"])

        if start <= current_time < end:
            return True

    return False


def get_ticket_and_requirements(connection, ticket_id):
    """Load a ticket and its required skills."""
    ticket = connection.execute(
        """
        SELECT *
        FROM tickets
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()

    if ticket is None:
        raise ValueError(f"Ticket not found: {ticket_id}")

    required_skills = connection.execute(
        """
        SELECT skill_id
        FROM skill_intents
        WHERE intent_id = ?
          AND is_required = 1
        ORDER BY skill_id
        """,
        (ticket["intent_id"],),
    ).fetchall()

    return ticket, {
        row["skill_id"] for row in required_skills
    }


def get_agent_workload(
    connection,
    agent_id,
    routing_time,
    exclude_ticket_id=None,
):
    """
    Count tickets assigned to an agent that were active
    at the requested historical routing time.

    Assignment history determines the responsible agent.

    Ticket creation and resolution timestamps determine
    whether the ticket existed and was still active.

    This avoids treating tickets resolved after the
    routing time as already completed.
    """

    timestamp = (
        routing_time
        .astimezone(ZoneInfo(DEFAULT_TIMEZONE))
        .replace(tzinfo=None)
        .isoformat()
    )

    placeholders = ",".join(
        "?" for _ in ACTIVE_STATUSES
    )

    query = f"""
        WITH latest_assignment AS (
            SELECT
                ae.ticket_id,
                ae.to_agent_id,

                ROW_NUMBER() OVER (
                    PARTITION BY ae.ticket_id
                    ORDER BY
                        ae.assigned_at DESC,
                        ae.assignment_event_id DESC
                ) AS rn

            FROM assignment_events ae

            WHERE ae.assigned_at <= ?
        )

        SELECT COUNT(*) AS workload

        FROM tickets t

        JOIN latest_assignment la
          ON la.ticket_id = t.ticket_id
         AND la.rn = 1

        WHERE t.created_at <= ?

          AND la.to_agent_id = ?

          AND (
              ? IS NULL
              OR t.ticket_id != ?
          )

          AND (
              t.status IN ({placeholders})

              OR (
                  t.status IN ('resolved', 'closed')
                  AND t.resolved_at IS NOT NULL
                  AND t.resolved_at > ?
              )
          )
    """

    parameters = (
        timestamp,
        timestamp,
        agent_id,
        exclude_ticket_id,
        exclude_ticket_id,
        *ACTIVE_STATUSES,
        timestamp,
    )

    row = connection.execute(
        query,
        parameters,
    ).fetchone()

    return row["workload"]


def get_queue_for_ticket(connection, ticket):
    """Find an active queue matching the ticket intent."""
    matching_queues = connection.execute(
        """
        SELECT q.queue_id, q.queue_name
        FROM queues q
        JOIN queue_intents qi
          ON qi.queue_id = q.queue_id
        WHERE qi.intent_id = ?
          AND q.is_active = 1
        ORDER BY q.queue_id
        """,
        (ticket["intent_id"],),
    ).fetchall()

    if not matching_queues:
        return None

    for queue in matching_queues:
        if queue["queue_id"] == ticket["queue_id"]:
            return dict(queue)

    return dict(matching_queues[0])


def make_not_routable_result(ticket):
    """Return a result for a ticket that must not be reassigned."""
    status = ticket["status"]

    return {
        "ticket_id": ticket["ticket_id"],
        "decision": "not_routable",
        "assigned_agent_id": ticket["assigned_agent_id"],
        "assigned_agent_name": None,
        "queue_id": ticket["queue_id"],
        "queue_name": None,
        "status": status,
        "routing_score": None,
        "reason": (
            f"Ticket cannot be routed because its status "
            f"is '{status}'"
        ),
        "candidates": [],
        "rejected_agents": [],
    }


def evaluate_ticket_routing(
    ticket_id,
    db_path=None,
    routing_at=None,
):
    """
    Recommend an agent without modifying the database.

    Eligibility checks:
    - Required skills and proficiency
    - Required language and proficiency
    - Working shift
    - Agent availability
    - Historical concurrent ticket capacity

    Returns an assignment, queue or not-routable decision.
    """

    database_path = (
        Path(db_path) if db_path else DEFAULT_DB_PATH
    )

    if not database_path.exists():
        raise FileNotFoundError(
            f"Generated database not found: {database_path}"
        )

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        ticket, required_skills = (
            get_ticket_and_requirements(
                connection,
                ticket_id,
            )
        )

        # Do not route completed or already-handled tickets.
        if ticket["status"] not in ROUTABLE_STATUSES:
            return make_not_routable_result(ticket)

        # Determine the time at which routing is evaluated.
        if routing_at is None:
            routing_time = parse_routing_datetime(
                ticket["created_at"]
            )
        else:
            routing_time = parse_routing_datetime(
                routing_at
            )

        agents = connection.execute(
            """
            SELECT *
            FROM agents
            WHERE is_active = 1
              AND status IN ('available', 'busy')
            ORDER BY agent_id
            """
        ).fetchall()

        candidates = []
        rejected = []

        for agent in agents:
            agent_id = agent["agent_id"]

            # 1. Required skill check.
            agent_skills = connection.execute(
                """
                SELECT skill_id, proficiency
                FROM agent_skills
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchall()

            skill_map = {
                row["skill_id"]: row["proficiency"]
                for row in agent_skills
            }

            missing_skills = [
                skill_id
                for skill_id in required_skills
                if skill_map.get(
                    skill_id, 0
                ) < MIN_SKILL_PROFICIENCY
            ]

            if missing_skills:
                rejected.append({
                    "agent_id": agent_id,
                    "reason": (
                        "Missing required skills "
                        "or proficiency"
                    ),
                })
                continue

            if required_skills:
                skill_score = sum(
                    skill_map[skill_id] / 5
                    for skill_id in required_skills
                ) / len(required_skills)
            else:
                skill_score = 1.0

            # 2. Language check.
            language_row = connection.execute(
                """
                SELECT proficiency
                FROM agent_languages
                WHERE agent_id = ?
                  AND language_id = ?
                """,
                (
                    agent_id,
                    ticket["language_id"],
                ),
            ).fetchone()

            if (
                language_row is None
                or language_row["proficiency"]
                < MIN_LANGUAGE_PROFICIENCY
            ):
                rejected.append({
                    "agent_id": agent_id,
                    "reason": (
                        "Required language not supported"
                    ),
                })
                continue

            language_score = (
                language_row["proficiency"] / 5
            )

            # 3. Working shift check.
            shifts = connection.execute(
                """
                SELECT day_of_week, start_time, end_time
                FROM agent_shifts
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchall()

            if not is_agent_on_shift(
                agent,
                shifts,
                routing_time,
            ):
                rejected.append({
                    "agent_id": agent_id,
                    "reason": "Outside working shift",
                })
                continue

            # 4. Historical capacity check.
            capacity = agent["max_concurrent_tickets"]

            workload = get_agent_workload(
                connection,
                agent_id,
                routing_time,
                ticket_id,
            )

            if capacity <= 0 or workload >= capacity:
                rejected.append({
                    "agent_id": agent_id,
                    "reason": (
                        "Agent has reached ticket capacity"
                    ),
                })
                continue

            # 5. Weighted routing score.
            availability_score = (
                1.0
                if agent["status"] == "available"
                else 0.75
            )

            capacity_score = (
                (capacity - workload) / capacity
            )

            workload_score = (
                1 - (workload / capacity)
            )

            score = (
                WEIGHTS["skill"] * skill_score
                + WEIGHTS["language"] * language_score
                + WEIGHTS["availability"] * availability_score
                + WEIGHTS["capacity"] * capacity_score
                + WEIGHTS["workload"] * workload_score
            )

            candidates.append({
                "agent_id": agent_id,
                "agent_name": agent["agent_name"],
                "workload": workload,
                "capacity": capacity,
                "routing_score": round(score, 4),
                "skill_score": round(skill_score, 4),
                "language_score": round(language_score, 4),
                "availability_score": availability_score,
                "capacity_score": round(capacity_score, 4),
                "workload_score": round(workload_score, 4),
            })

        # Deterministic ranking: highest score first.
        candidates.sort(
            key=lambda candidate: (
                -candidate["routing_score"],
                candidate["agent_id"],
            )
        )

        # An eligible agent was found.
        if candidates:
            best = candidates[0]

            return {
                "ticket_id": ticket_id,
                "decision": "assigned",
                "assigned_agent_id": best["agent_id"],
                "assigned_agent_name": best["agent_name"],
                "queue_id": None,
                "queue_name": None,
                "status": "assigned",
                "routing_score": best["routing_score"],
                "reason": (
                    "Best eligible agent based "
                    "on routing score"
                ),
                "candidates": candidates,
                "rejected_agents": rejected,
            }

        # No eligible agent: recommend a matching queue.
        queue = get_queue_for_ticket(
            connection,
            ticket,
        )

        return {
            "ticket_id": ticket_id,
            "decision": "queued",
            "assigned_agent_id": None,
            "assigned_agent_name": None,
            "queue_id": (
                queue["queue_id"] if queue else None
            ),
            "queue_name": (
                queue["queue_name"] if queue else None
            ),
            "status": "queued",
            "routing_score": None,
            "reason": (
                "No eligible agent is currently available"
            ),
            "candidates": [],
            "rejected_agents": rejected,
        }
