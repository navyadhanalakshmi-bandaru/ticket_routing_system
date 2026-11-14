# Data dictionary

Generated from the SQLite schema by scripts/make_data_dictionary.py.
All data is synthetic (seed in config/settings.py); no external or personal data is used.

## agent_languages (380 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| agent_id | TEXT | yes | PK (unique) | e.g. AGT-000001 |
| language_id | INTEGER | yes | PK (unique) | 1, 2, 3, 4, 5, 6, 7 |
| proficiency | INTEGER | yes |  | 5, 3, 4 |

## agent_shifts (575 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| shift_id | INTEGER | yes | PK (unique) | e.g. 1 |
| agent_id | TEXT | yes | FK -> agents.agent_id | e.g. AGT-000001 |
| day_of_week | INTEGER | yes |  | 0, 1, 2, 3, 4, 5, 6 |
| start_time | TEXT | yes |  | 09:00, 10:00, 08:00 |
| end_time | TEXT | yes |  | 17:00, 18:00, 16:00 |
| timezone | TEXT | yes |  | Asia/Kolkata |

## agent_skills (480 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| agent_id | TEXT | yes | PK (unique) | e.g. AGT-000001 |
| skill_id | INTEGER | yes | PK (unique) | 1, 2, 3, 4, 5, 6, 7, 8 |
| proficiency | INTEGER | yes |  | 5, 3, 4 |

## agents (100 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| agent_id | TEXT | yes | PK (unique) | e.g. AGT-000001 |
| agent_name | TEXT | yes |  | e.g. Daniel Estrada |
| email | TEXT | yes |  | e.g. agent100@example.com |
| status | TEXT | yes |  | available, away, busy, offline |
| max_concurrent_tickets | INTEGER | yes |  | 5, 8, 4, 7, 6 |
| timezone | TEXT | yes |  | Asia/Kolkata |
| hire_date | TEXT | no |  | e.g. 2023-09-22 |
| is_active | INTEGER | yes |  | 1 |

## anomaly_labels (5 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| anomaly_id | TEXT | yes | PK (unique) | ANM-000001, ANM-000002, ANM-000003, ANM-000004, ANM-000005 |
| ticket_id | TEXT | yes | FK -> tickets.ticket_id | TKT-2026-019036, TKT-2026-005352, TKT-2026-021053, TKT-2026-022931, TKT-2026-002229 |
| scenario_name | TEXT | yes |  | agent_over_capacity, sla_ignores_channel_calendar, reopened_ticket_loses_history, transfer_loop, priority_contradicts_safety_rule |
| expected_issue | TEXT | yes |  | Agent exceeds concurrent capacity of 5., SLA deadline does not account for channel business hours., Reopened ticket has lost its previous lifecycle events., Ticket repeatedly transfers between the same two agents., Safety-related ticket has Low priority instead of Critical. |

## assignment_events (30003 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| assignment_event_id | TEXT | yes | PK (unique) | e.g. ASN-000001-001 |
| ticket_id | TEXT | yes | FK -> tickets.ticket_id | e.g. TKT-2026-000001 |
| from_agent_id | TEXT | no | FK -> agents.agent_id | None, AGT-000001, AGT-000002 |
| to_agent_id | TEXT | no | FK -> agents.agent_id | e.g. AGT-000001 |
| from_queue_id | INTEGER | no | FK -> queues.queue_id | None, 4 |
| to_queue_id | INTEGER | no | FK -> queues.queue_id | 3, 2, 6, 4, 5, 1 |
| assigned_at | TEXT | yes |  | e.g. 2026-08-17T00:24:07 |
| assignment_reason | TEXT | yes |  | Initial synthetic assignment, ANOMALY: repeated transfer loop |
| routing_score | REAL | no |  | e.g. 68.13 |
| event_type | TEXT | yes |  | assign, transfer |

## business_calendars (4 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| calendar_id | INTEGER | yes | PK (unique) | 2, 1, 3, 4 |
| calendar_name | TEXT | yes |  | Chat Calendar, Email Calendar, Phone Calendar, Web Calendar |
| timezone | TEXT | yes |  | Asia/Kolkata |
| monday_open | TEXT | no |  | 09:00, 00:00 |
| monday_close | TEXT | no |  | 17:00, 23:59 |
| tuesday_open | TEXT | no |  | 09:00, 00:00 |
| tuesday_close | TEXT | no |  | 17:00, 23:59 |
| wednesday_open | TEXT | no |  | 09:00, 00:00 |
| wednesday_close | TEXT | no |  | 17:00, 23:59 |
| thursday_open | TEXT | no |  | 09:00, 00:00 |
| thursday_close | TEXT | no |  | 17:00, 23:59 |
| friday_open | TEXT | no |  | 09:00, 00:00 |
| friday_close | TEXT | no |  | 17:00, 23:59 |
| saturday_open | TEXT | no |  | 09:00, 00:00 |
| saturday_close | TEXT | no |  | 13:00, 23:59 |
| sunday_open | TEXT | no |  | None, 00:00 |
| sunday_close | TEXT | no |  | None, 23:59 |

## calendar_holidays (0 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| holiday_id | INTEGER | yes | PK (unique) |  |
| calendar_id | INTEGER | yes | FK -> business_calendars.calendar_id |  |
| holiday_date | TEXT | yes |  |  |
| holiday_name | TEXT | yes |  |  |

## channel_calendars (4 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| channel_id | INTEGER | yes | PK (unique) | 1, 2, 3, 4 |
| calendar_id | INTEGER | yes | FK -> business_calendars.calendar_id | 1, 2, 3, 4 |

## channels (4 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| channel_id | INTEGER | yes | PK (unique) | 2, 1, 3, 4 |
| channel_name | TEXT | yes |  | chat, email, phone, web |
| is_active | INTEGER | yes |  | 1 |

## customers (10000 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| customer_id | TEXT | yes | PK (unique) | e.g. CUS-000001 |
| customer_name | TEXT | yes |  | e.g. Lauren Nash |
| email | TEXT | no |  | e.g. customer1@example.com |
| phone | TEXT | no |  | e.g. 5336308203 |
| customer_tier | TEXT | yes |  | Silver, Standard, Gold, Platinum |
| created_at | TEXT | yes |  | e.g. 2025-12-25T10:16:28 |
| country | TEXT | no |  | e.g. Reunion |

## intents (9 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| intent_id | INTEGER | yes | PK (unique) | 3, 1, 6, 5, 9, 7, 4, 8, 2 |
| intent_name | TEXT | yes |  | Account Access, Billing, Cancellation, Delivery, Fraud Report, Product Information, Refund, Security Incident, Technical Support |
| description | TEXT | no |  | Billing and payment questions, Technical problems, Account access issues, Refund requests, Delivery and shipment, Cancellation requests, Product questions, Account security incidents, Suspected fraudulent activity |
| default_priority | TEXT | yes |  | Medium, High, Low, Critical |
| is_safety_related | INTEGER | yes |  | 0, 1 |

## languages (7 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| language_id | INTEGER | yes | PK (unique) | 7, 1, 5, 6, 2, 4, 3 |
| language_code | TEXT | yes |  | de, en, es, fr, hi, ta, te |
| language_name | TEXT | yes |  | English, Hindi, Telugu, Tamil, Spanish, French, German |

## messages (100000 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| message_id | TEXT | yes | PK (unique) | e.g. MSG-000001-001 |
| ticket_id | TEXT | yes | FK -> tickets.ticket_id | e.g. TKT-2026-000001 |
| sender_type | TEXT | yes |  | customer, agent |
| sender_id | TEXT | no |  | e.g. CUS-009017 |
| message_text | TEXT | yes |  | I would like to request further information., Thank you for your assistance., The issue has been resolved., I need help with this issue., Could you please check my request?, I am still experiencing the problem., Please provide an update. |
| sent_at | TEXT | yes |  | e.g. 2026-09-23T00:57:14 |
| is_internal | INTEGER | yes |  | 0 |

## priority_rules (9 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| priority_rule_id | INTEGER | yes | PK (unique) | 3, 1, 6, 5, 9, 7, 4, 8, 2 |
| rule_name | TEXT | yes |  | Account Access default rule, Billing default rule, Cancellation default rule, Delivery default rule, Fraud Report default rule, Product Information default rule, Refund default rule, Security Incident default rule, Technical Support default rule |
| intent_id | INTEGER | no | FK -> intents.intent_id | 1, 2, 3, 4, 5, 6, 7, 8, 9 |
| customer_tier | TEXT | no |  | None |
| channel_id | INTEGER | no | FK -> channels.channel_id | None |
| priority | TEXT | yes |  | Medium, High, Low, Critical |
| priority_floor | TEXT | no |  | None, Critical |
| rule_order | INTEGER | yes |  | 1 |
| is_active | INTEGER | yes |  | 1 |

## queue_intents (12 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| queue_id | INTEGER | yes | PK (unique) | 1, 2, 3, 4, 5, 6 |
| intent_id | INTEGER | yes | PK (unique) | 7, 6, 3, 1, 4, 2, 8, 9, 5 |

## queues (6 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| queue_id | INTEGER | yes | PK (unique) | 4, 2, 5, 1, 6, 3 |
| queue_name | TEXT | yes |  | Account Security, Billing Support, Delivery Support, General Support, Priority Escalation, Technical Support |
| description | TEXT | no |  | Queue for general support, Queue for billing support, Queue for technical support, Queue for account security, Queue for delivery support, Queue for priority escalation |
| is_active | INTEGER | yes |  | 1 |

## resolutions (29858 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| resolution_id | TEXT | yes | PK (unique) | e.g. RES-000001-001 |
| ticket_id | TEXT | yes | FK -> tickets.ticket_id | e.g. TKT-2026-000001 |
| resolution_number | INTEGER | yes |  | 1 |
| resolved_by_agent_id | TEXT | no | FK -> agents.agent_id | e.g. AGT-000041 |
| resolution_category | TEXT | yes |  | Issue Fixed, Refund Processed, Account Restored, Technical Resolution, Information Provided |
| resolution_notes | TEXT | no |  | Synthetic resolution record |
| resolved_at | TEXT | yes |  | e.g. 2026-09-24T00:17:14 |
| csat_score | INTEGER | no |  | 2, 5, 1, 4, 3 |
| customer_feedback | TEXT | no |  | Thank you for your support. |

## skill_intents (17 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| skill_id | INTEGER | yes | PK (unique) | 1, 2, 3, 4, 5, 6, 7, 8 |
| intent_id | INTEGER | yes | PK (unique) | 1, 4, 9, 2, 3, 6, 8, 5, 7 |
| is_required | INTEGER | yes |  | 1 |

## skills (8 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| skill_id | INTEGER | yes | PK (unique) | 3, 1, 7, 5, 8, 4, 6, 2 |
| skill_name | TEXT | yes |  | Account Management, Billing Support, Customer Communication, Delivery Support, Product Knowledge, Refund Processing, Security Investigation, Technical Troubleshooting |
| description | TEXT | no |  | Handles billing support cases, Handles technical troubleshooting cases, Handles account management cases, Handles refund processing cases, Handles delivery support cases, Handles security investigation cases, Handles customer communication cases, Handles product knowledge cases |

## sla_events (60000 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| sla_event_id | TEXT | yes | PK (unique) | e.g. SLA-000001-001 |
| ticket_id | TEXT | yes | FK -> tickets.ticket_id | e.g. TKT-2026-000001 |
| event_type | TEXT | yes |  | created, response_met |
| target_at | TEXT | no |  | e.g. 2026-09-23T09:05:00 |
| occurred_at | TEXT | yes |  | e.g. 2026-09-23T00:53:14 |
| is_breach | INTEGER | yes |  | 0, 1 |
| details | TEXT | no |  | Initial response SLA target, Synthetic first response, ANOMALY: elapsed-time SLA ignores channel calendar. |

## sla_policies (16 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| sla_policy_id | INTEGER | yes | PK (unique) | e.g. 1 |
| policy_name | TEXT | yes |  | e.g. Critical email SLA |
| priority | TEXT | yes |  | Critical, High, Low, Medium |
| channel_id | INTEGER | yes | FK -> channels.channel_id | 1, 2, 3, 4 |
| response_minutes | INTEGER | yes |  | 5, 15, 60, 240 |
| resolution_minutes | INTEGER | yes |  | 60, 240, 1440, 4320 |
| calendar_id | INTEGER | no | FK -> business_calendars.calendar_id | 1, 2, 3, 4 |
| is_active | INTEGER | yes |  | 1 |

## ticket_events (59998 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| ticket_event_id | TEXT | yes | PK (unique) | e.g. EVT-000001-001 |
| ticket_id | TEXT | yes | FK -> tickets.ticket_id | e.g. TKT-2026-000001 |
| event_type | TEXT | yes |  | created, assigned |
| old_status | TEXT | no |  | None, open |
| new_status | TEXT | no |  | open, assigned |
| event_at | TEXT | yes |  | e.g. 2026-09-23T00:53:14 |
| actor_type | TEXT | yes |  | system |
| actor_id | TEXT | no |  | None |
| notes | TEXT | no |  | Ticket created, Agent assigned |

## tickets (30000 rows)

| Column | Type | Required | Key | Allowed values / example |
|---|---|---|---|---|
| ticket_id | TEXT | yes | PK (unique) | e.g. TKT-2026-000001 |
| customer_id | TEXT | yes | FK -> customers.customer_id | e.g. CUS-009017 |
| channel_id | INTEGER | yes | FK -> channels.channel_id | 1, 2, 3, 4 |
| intent_id | INTEGER | yes | FK -> intents.intent_id | 6, 8, 9, 3, 1, 7, 2, 5, 4 |
| language_id | INTEGER | yes | FK -> languages.language_id | 6, 2, 7, 1, 3, 4, 5 |
| queue_id | INTEGER | no | FK -> queues.queue_id | 1, 2, 3, 4, 5, 6 |
| assigned_agent_id | TEXT | no | FK -> agents.agent_id | e.g. AGT-000001 |
| subject | TEXT | yes |  | Technical problem, Product information request, Order not delivered, Payment issue, Subscription cancellation, Refund request, Unable to access account, Account security concern |
| description | TEXT | no |  | Customer request concerning cancellation., Customer request concerning security incident., Customer request concerning fraud report., Customer request concerning account access., Customer request concerning billing., Customer request concerning product information., Customer request concerning technical support., Customer request concerning delivery., Customer request concerning refund. |
| priority | TEXT | yes |  | Critical, High, Low, Medium |
| status | TEXT | yes |  | closed, in_progress, pending_customer, queued, reopened, resolved |
| created_at | TEXT | yes |  | e.g. 2026-08-17T00:05:06 |
| first_response_at | TEXT | no |  | e.g. 2026-09-23T01:28:14 |
| resolved_at | TEXT | no |  | e.g. 2026-09-24T00:17:14 |
| closed_at | TEXT | no |  | e.g. None |
| reopened_count | INTEGER | yes |  | 0, 1 |
| source_reference | TEXT | no |  | e.g. SRC-00000001 |

## Relationships (foreign keys)

- agent_languages.language_id -> languages.language_id (N:1)
- agent_languages.agent_id -> agents.agent_id (N:1)
- agent_shifts.agent_id -> agents.agent_id (N:1)
- agent_skills.skill_id -> skills.skill_id (N:1)
- agent_skills.agent_id -> agents.agent_id (N:1)
- anomaly_labels.ticket_id -> tickets.ticket_id (N:1)
- assignment_events.to_queue_id -> queues.queue_id (N:1)
- assignment_events.from_queue_id -> queues.queue_id (N:1)
- assignment_events.to_agent_id -> agents.agent_id (N:1)
- assignment_events.from_agent_id -> agents.agent_id (N:1)
- assignment_events.ticket_id -> tickets.ticket_id (N:1)
- calendar_holidays.calendar_id -> business_calendars.calendar_id (N:1)
- channel_calendars.calendar_id -> business_calendars.calendar_id (N:1)
- channel_calendars.channel_id -> channels.channel_id (N:1)
- messages.ticket_id -> tickets.ticket_id (N:1)
- priority_rules.channel_id -> channels.channel_id (N:1)
- priority_rules.intent_id -> intents.intent_id (N:1)
- queue_intents.intent_id -> intents.intent_id (N:1)
- queue_intents.queue_id -> queues.queue_id (N:1)
- resolutions.resolved_by_agent_id -> agents.agent_id (N:1)
- resolutions.ticket_id -> tickets.ticket_id (N:1)
- skill_intents.intent_id -> intents.intent_id (N:1)
- skill_intents.skill_id -> skills.skill_id (N:1)
- sla_events.ticket_id -> tickets.ticket_id (N:1)
- sla_policies.calendar_id -> business_calendars.calendar_id (N:1)
- sla_policies.channel_id -> channels.channel_id (N:1)
- ticket_events.ticket_id -> tickets.ticket_id (N:1)
- tickets.assigned_agent_id -> agents.agent_id (N:1)
- tickets.queue_id -> queues.queue_id (N:1)
- tickets.language_id -> languages.language_id (N:1)
- tickets.intent_id -> intents.intent_id (N:1)
- tickets.channel_id -> channels.channel_id (N:1)
- tickets.customer_id -> customers.customer_id (N:1)