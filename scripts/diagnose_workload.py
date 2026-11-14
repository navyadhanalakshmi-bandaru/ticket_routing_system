"""Shows ticket status by age and agents over capacity. Read-only."""
import sqlite3
import pandas as pd

conn = sqlite3.connect("outputs/ticket_routing_generated.db")
ACTIVE = ["in_progress", "pending_customer", "reopened"]

df = pd.read_sql_query(
    "SELECT ticket_id, assigned_agent_id, status, created_at, resolved_at FROM tickets", conn)
df["created"] = pd.to_datetime(df["created_at"])
age_days = (pd.Timestamp("2026-11-14 23:59:59") - df["created"]).dt.days
df["age_bucket"] = pd.cut(age_days, [-1, 2, 7, 30, 1000],
                          labels=["0-2d", "3-7d", "8-30d", "31d+"])

print("Status by ticket age:")
print(pd.crosstab(df["age_bucket"], df["status"]))

cap = pd.read_sql_query(
    "SELECT agent_id, max_concurrent_tickets AS cap FROM agents WHERE is_active=1", conn)
active = df[df["status"].isin(ACTIVE)].groupby("assigned_agent_id").size().rename("active")
merged = cap.merge(active, left_on="agent_id", right_index=True, how="left").fillna({"active": 0})
print("\nTotal capacity:", int(cap["cap"].sum()))
print("Active tickets:", int(merged["active"].sum()))
print("Agents over capacity:", int((merged["active"] > merged["cap"]).sum()), "of", len(merged))

print("\nAnomaly labels (ground truth):")
for row in conn.execute("SELECT * FROM anomaly_labels"):
    print(row)
conn.close()