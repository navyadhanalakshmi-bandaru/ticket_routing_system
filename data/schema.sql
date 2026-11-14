
PRAGMA foreign_keys = ON;

-- 1. Communication channels
CREATE TABLE IF NOT EXISTS channels (
    channel_id INTEGER PRIMARY KEY,
    channel_name TEXT NOT NULL UNIQUE
        CHECK (channel_name IN ('email', 'chat', 'phone', 'web')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

-- 2. Supported languages
CREATE TABLE IF NOT EXISTS languages (
    language_id INTEGER PRIMARY KEY,
    language_code TEXT NOT NULL UNIQUE,
    language_name TEXT NOT NULL
);

-- 3. Customer intents
CREATE TABLE IF NOT EXISTS intents (
    intent_id INTEGER PRIMARY KEY,
    intent_name TEXT NOT NULL UNIQUE,
    description TEXT,
    default_priority TEXT NOT NULL DEFAULT 'Medium'
        CHECK (default_priority IN ('Critical', 'High', 'Medium', 'Low')),
    is_safety_related INTEGER NOT NULL DEFAULT 0
        CHECK (is_safety_related IN (0, 1))
);

-- 4. Agent skills
CREATE TABLE IF NOT EXISTS skills (
    skill_id INTEGER PRIMARY KEY,
    skill_name TEXT NOT NULL UNIQUE,
    description TEXT
);

-- 5. Routing queues
CREATE TABLE IF NOT EXISTS queues (
    queue_id INTEGER PRIMARY KEY,
    queue_name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

-- 6. Customers
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    customer_tier TEXT NOT NULL DEFAULT 'Standard'
        CHECK (customer_tier IN ('Standard', 'Silver', 'Gold', 'Platinum')),
    created_at TEXT NOT NULL,
    country TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_email
ON customers(email) WHERE email IS NOT NULL;

-- 7. Support agents
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'busy', 'away', 'offline')),
    max_concurrent_tickets INTEGER NOT NULL DEFAULT 5
        CHECK (max_concurrent_tickets > 0),
    timezone TEXT NOT NULL DEFAULT 'UTC',
    hire_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

-- 8. Priority rules
CREATE TABLE IF NOT EXISTS priority_rules (
    priority_rule_id INTEGER PRIMARY KEY,
    rule_name TEXT NOT NULL UNIQUE,
    intent_id INTEGER,
    customer_tier TEXT,
    channel_id INTEGER,
    priority TEXT NOT NULL
        CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
    priority_floor TEXT
        CHECK (priority_floor IN ('Critical', 'High', 'Medium', 'Low')),
    rule_order INTEGER NOT NULL DEFAULT 100,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
);

-- 9. Support tickets
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    channel_id INTEGER NOT NULL,
    intent_id INTEGER NOT NULL,
    language_id INTEGER NOT NULL,
    queue_id INTEGER,
    assigned_agent_id TEXT,
    subject TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL
        CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN (
            'open', 'queued', 'assigned', 'in_progress',
            'pending_customer', 'resolved', 'closed', 'reopened'
        )),
    created_at TEXT NOT NULL,
    first_response_at TEXT,
    resolved_at TEXT,
    closed_at TEXT,
    reopened_count INTEGER NOT NULL DEFAULT 0
        CHECK (reopened_count >= 0),
    source_reference TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id),
    FOREIGN KEY (language_id) REFERENCES languages(language_id),
    FOREIGN KEY (queue_id) REFERENCES queues(queue_id),
    FOREIGN KEY (assigned_agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_tickets_status_priority
ON tickets(status, priority);

CREATE INDEX IF NOT EXISTS idx_tickets_created_at
ON tickets(created_at);

CREATE INDEX IF NOT EXISTS idx_tickets_agent
ON tickets(assigned_agent_id);

CREATE INDEX IF NOT EXISTS idx_tickets_queue
ON tickets(queue_id);

-- 10. Ticket messages
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    sender_type TEXT NOT NULL
        CHECK (sender_type IN ('customer', 'agent', 'system')),
    sender_id TEXT,
    message_text TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    is_internal INTEGER NOT NULL DEFAULT 0
        CHECK (is_internal IN (0, 1)),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_ticket_time
ON messages(ticket_id, sent_at);

-- 11. Assignment history (append-only events)
CREATE TABLE IF NOT EXISTS assignment_events (
    assignment_event_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    from_agent_id TEXT,
    to_agent_id TEXT,
    from_queue_id INTEGER,
    to_queue_id INTEGER,
    assigned_at TEXT NOT NULL,
    assignment_reason TEXT NOT NULL,
    routing_score REAL,
    event_type TEXT NOT NULL
        CHECK (event_type IN ('assign', 'transfer', 'unassign', 'queue')),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (from_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (to_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (from_queue_id) REFERENCES queues(queue_id),
    FOREIGN KEY (to_queue_id) REFERENCES queues(queue_id)
);

CREATE INDEX IF NOT EXISTS idx_assignment_ticket_time
ON assignment_events(ticket_id, assigned_at);

CREATE INDEX IF NOT EXISTS idx_assignment_agent_time
ON assignment_events(to_agent_id, assigned_at);

-- 12. SLA tracking events
CREATE TABLE IF NOT EXISTS sla_events (
    sla_event_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    event_type TEXT NOT NULL
        CHECK (event_type IN (
            'created', 'response_due', 'response_met',
            'resolution_due', 'resolution_met',
            'breached', 'escalated', 'paused', 'resumed'
        )),
    target_at TEXT,
    occurred_at TEXT NOT NULL,
    is_breach INTEGER NOT NULL DEFAULT 0
        CHECK (is_breach IN (0, 1)),
    details TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
);

CREATE INDEX IF NOT EXISTS idx_sla_ticket_time
ON sla_events(ticket_id, occurred_at);

-- 13. Ticket resolutions
CREATE TABLE IF NOT EXISTS resolutions (
    resolution_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    resolution_number INTEGER NOT NULL DEFAULT 1
        CHECK (resolution_number > 0),
    resolved_by_agent_id TEXT,
    resolution_category TEXT NOT NULL,
    resolution_notes TEXT,
    resolved_at TEXT NOT NULL,
    csat_score INTEGER CHECK (csat_score BETWEEN 1 AND 5),
    customer_feedback TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
    FOREIGN KEY (resolved_by_agent_id) REFERENCES agents(agent_id),
    UNIQUE (ticket_id, resolution_number)
);

-- Supporting relationship: agent-to-skill
CREATE TABLE IF NOT EXISTS agent_skills (
    agent_id TEXT NOT NULL,
    skill_id INTEGER NOT NULL,
    proficiency INTEGER NOT NULL DEFAULT 3
        CHECK (proficiency BETWEEN 1 AND 5),
    PRIMARY KEY (agent_id, skill_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

-- Supporting relationship: agent-to-language
CREATE TABLE IF NOT EXISTS agent_languages (
    agent_id TEXT NOT NULL,
    language_id INTEGER NOT NULL,
    proficiency INTEGER NOT NULL DEFAULT 3
        CHECK (proficiency BETWEEN 1 AND 5),
    PRIMARY KEY (agent_id, language_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (language_id) REFERENCES languages(language_id)
);

-- Which skills are required for each intent?
CREATE TABLE IF NOT EXISTS skill_intents (
    skill_id INTEGER NOT NULL,
    intent_id INTEGER NOT NULL,
    is_required INTEGER NOT NULL DEFAULT 1
        CHECK (is_required IN (0, 1)),
    PRIMARY KEY (skill_id, intent_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id),
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id)
);

-- Which intents can each queue handle?
CREATE TABLE IF NOT EXISTS queue_intents (
    queue_id INTEGER NOT NULL,
    intent_id INTEGER NOT NULL,
    PRIMARY KEY (queue_id, intent_id),
    FOREIGN KEY (queue_id) REFERENCES queues(queue_id),
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id)
);

-- Append-only ticket lifecycle history
CREATE TABLE IF NOT EXISTS ticket_events (
    ticket_event_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    event_at TEXT NOT NULL,
    actor_type TEXT NOT NULL
        CHECK (actor_type IN ('customer', 'agent', 'system')),
    actor_id TEXT,
    notes TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
);

CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket_time
ON ticket_events(ticket_id, event_at);

-- Business calendars for channel-specific SLA calculations
CREATE TABLE IF NOT EXISTS business_calendars (
    calendar_id INTEGER PRIMARY KEY,
    calendar_name TEXT NOT NULL UNIQUE,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    monday_open TEXT,
    monday_close TEXT,
    tuesday_open TEXT,
    tuesday_close TEXT,
    wednesday_open TEXT,
    wednesday_close TEXT,
    thursday_open TEXT,
    thursday_close TEXT,
    friday_open TEXT,
    friday_close TEXT,
    saturday_open TEXT,
    saturday_close TEXT,
    sunday_open TEXT,
    sunday_close TEXT
);

CREATE TABLE IF NOT EXISTS channel_calendars (
    channel_id INTEGER PRIMARY KEY,
    calendar_id INTEGER NOT NULL,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    FOREIGN KEY (calendar_id) REFERENCES business_calendars(calendar_id)
);

CREATE TABLE IF NOT EXISTS calendar_holidays (
    holiday_id INTEGER PRIMARY KEY,
    calendar_id INTEGER NOT NULL,
    holiday_date TEXT NOT NULL,
    holiday_name TEXT NOT NULL,
    UNIQUE (calendar_id, holiday_date),
    FOREIGN KEY (calendar_id) REFERENCES business_calendars(calendar_id)
);

-- Agent working shifts
CREATE TABLE IF NOT EXISTS agent_shifts (
    shift_id INTEGER PRIMARY KEY,
    agent_id TEXT NOT NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- SLA policy targets by priority and channel
CREATE TABLE IF NOT EXISTS sla_policies (
    sla_policy_id INTEGER PRIMARY KEY,
    policy_name TEXT NOT NULL,
    priority TEXT NOT NULL
        CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
    channel_id INTEGER NOT NULL,
    response_minutes INTEGER NOT NULL CHECK (response_minutes > 0),
    resolution_minutes INTEGER NOT NULL CHECK (resolution_minutes > 0),
    calendar_id INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    UNIQUE (priority, channel_id, policy_name),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    FOREIGN KEY (calendar_id) REFERENCES business_calendars(calendar_id)
);

-- Anomaly scenario labels are kept separate from routing inputs.
CREATE TABLE IF NOT EXISTS anomaly_labels (
    anomaly_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    scenario_name TEXT NOT NULL,
    expected_issue TEXT NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
);
