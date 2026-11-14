"""Repairs baseline data so only the injected anomalies remain.
1. created-event SLA targets -> calendar-based response deadline.
2. Capacity-aware reassignment (within the agents already seen on the same queue).
Run AFTER python -m generator.generate. Safe to re-run."""
import heapq
import shutil
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anomaly_detector import DEFAULT_DB_PATH
from services.sla_engine import (calculate_sla_deadline, load_calendar,
                                 load_holidays, load_policy)

shutil.copy(DEFAULT_DB_PATH, str(DEFAULT_DB_PATH) + ".bak")
conn = sqlite3.connect(DEFAULT_DB_PATH)
INF = datetime.max

# ---------------------------------------------------------------- 1. SLA
holidays = load_holidays(conn)
cal_cache, pol_cache, updates = {}, {}, []
rows = conn.execute(
    "SELECT s.sla_event_id, t.ticket_id, t.channel_id, t.priority, t.created_at "
    "FROM tickets t JOIN sla_events s ON s.ticket_id=t.ticket_id AND s.event_type='created'"
).fetchall()
sla_anomaly = {r[0] for r in conn.execute(
    "SELECT ticket_id FROM anomaly_labels WHERE scenario_name='sla_ignores_channel_calendar'")}
for sla_id, tid, ch, pr, created in rows:
    if tid in sla_anomaly:
        continue  # keep the deliberate wrong deadline
    if ch not in cal_cache:
        cal_cache[ch] = load_calendar(conn, ch)
    if (pr, ch) not in pol_cache:
        pol_cache[(pr, ch)] = load_policy(conn, pr, ch)
    due = calculate_sla_deadline(created, pol_cache[(pr, ch)]["response_minutes"],
                                 cal_cache[ch], holidays)
    updates.append((due.isoformat(), sla_id))
conn.executemany("UPDATE sla_events SET target_at=? WHERE sla_event_id=?", updates)
print(f"SLA targets rewritten: {len(updates)}")

# ---------------------------------------------------------------- 2. capacity
cap = dict(conn.execute("SELECT agent_id, max_concurrent_tickets FROM agents"))
all_agents = sorted(cap)
labeled = {r[0] for r in conn.execute("SELECT ticket_id FROM anomaly_labels")}

over = conn.execute(
    "SELECT t.assigned_agent_id FROM anomaly_labels l JOIN tickets t ON t.ticket_id=l.ticket_id "
    "WHERE l.scenario_name='agent_over_capacity'").fetchone()
blocked_agent = over[0] if over else None
protected = set()
if blocked_agent:
    newest = conn.execute("SELECT ticket_id FROM tickets ORDER BY created_at DESC, ticket_id DESC "
                          "LIMIT ?", (cap[blocked_agent] + 1,)).fetchall()
    protected = {r[0] for r in newest}

events = defaultdict(list)
for typ, tid, at in conn.execute("SELECT event_type, ticket_id, assigned_at FROM assignment_events"):
    events[tid].append((typ, at))

tickets = conn.execute(
    "SELECT ticket_id, queue_id, assigned_agent_id, created_at, resolved_at FROM tickets").fetchall()

items, pool = [], defaultdict(set)
for tid, queue, agent, created, resolved in tickets:
    if agent is None:
        continue
    evs = events.get(tid, [])
    simple = len(evs) >= 1 and all(t == "assign" for t, _ in evs)
    fixed = tid in labeled or tid in protected or not simple
    start = datetime.fromisoformat(min(a for _, a in evs) if evs else created)
    end = datetime.fromisoformat(resolved) if resolved else INF
    items.append((start, tid, queue, agent, end, fixed))
    if not fixed:
        pool[queue].add(agent)
items.sort(key=lambda x: (x[0], x[1]))

block_from = min((s for s, tid, *_ in items if tid in protected), default=None)
heaps = defaultdict(list)


def load(agent, now):
    h = heaps[agent]
    while h and h[0] <= now:
        heapq.heappop(h)
    return len(h)


def allowed(agent, end):
    if agent == blocked_agent and block_from is not None:
        return end != INF and end <= block_from
    return True


reassigned, unresolved, new_agent = 0, 0, {}
for start, tid, queue, agent, end, fixed in items:
    if fixed:
        load(agent, start)
        heapq.heappush(heaps[agent], end)
        continue
    chosen = None
    if allowed(agent, end) and load(agent, start) < cap[agent]:
        chosen = agent
    else:
        for group in (sorted(pool[queue]), all_agents):
            options = sorted((a for a in group if allowed(a, end)),
                             key=lambda a: (load(a, start), a))
            options = [a for a in options if load(a, start) < cap[a]]
            if options:
                chosen = options[0]
                break
    if chosen is None:
        chosen, unresolved = agent, unresolved + 1
    if chosen != agent:
        new_agent[tid] = chosen
        reassigned += 1
    heapq.heappush(heaps[chosen], end)

conn.executemany("UPDATE tickets SET assigned_agent_id=? WHERE ticket_id=?",
                 [(a, t) for t, a in new_agent.items()])
conn.executemany("UPDATE assignment_events SET to_agent_id=? WHERE ticket_id=? AND event_type='assign'",
                 [(a, t) for t, a in new_agent.items()])
res_cols = [c[1] for c in conn.execute("PRAGMA table_info(resolutions)")]
for col in ("resolved_by_agent_id", "agent_id"):
    if col in res_cols:
        conn.executemany(f"UPDATE resolutions SET {col}=? WHERE ticket_id=?",
                         [(a, t) for t, a in new_agent.items()])
conn.commit()
conn.close()
print(f"Tickets reassigned: {reassigned}; could not fit anywhere: {unresolved}")