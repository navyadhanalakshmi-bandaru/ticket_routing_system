import json
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.metrics import DEFAULT_DB_PATH, compute_all

out_dir = Path(DEFAULT_DB_PATH).parent / "reports"
out_dir.mkdir(parents=True, exist_ok=True)
m = compute_all()
(out_dir / "metrics.json").write_text(json.dumps(m, indent=2))

evaluation_path = out_dir / "anomaly_evaluation.json"
evaluation = json.loads(evaluation_path.read_text()) if evaluation_path.exists() else {}


def table(headers, rows):
    head = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def bar(pct):
    return f'<div class="bar"><div style="width:{min(pct, 100)}%"></div></div>'


sla = m["sla_compliance"]
cards = [("SLA response compliance", f'{sla["overall"]["rate_pct"]}%'),
         ("Tickets assigned", f'{m["routing"]["assigned_pct"]}%'),
         ("Agent utilisation", f'{m["utilisation"]["utilisation_pct"]}%'),
         ("Agents over capacity", m["utilisation"]["agents_over_capacity"])]
card_html = "".join(f'<div class="card"><h3>{escape(str(k))}</h3><p>{escape(str(v))}</p></div>'
                    for k, v in cards)

html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Ticket Routing Dashboard</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:2rem;color:#222}}
.cards{{display:flex;gap:1rem;flex-wrap:wrap}}
.card{{border:1px solid #ddd;border-radius:8px;padding:1rem 1.5rem;min-width:180px}}
.card h3{{margin:0;font-size:.85rem;color:#666}}.card p{{margin:.3rem 0 0;font-size:1.8rem;font-weight:600}}
table{{border-collapse:collapse;margin:.5rem 0 1.5rem}}td,th{{border:1px solid #ddd;padding:.35rem .8rem;text-align:left}}
th{{background:#f5f5f5}}.bar{{background:#eee;width:160px;height:10px;border-radius:5px}}
.bar div{{background:#3b82f6;height:10px;border-radius:5px}}
</style></head><body>
<h1>Ticket Routing Dashboard</h1><div class="cards">{card_html}</div>
<h2>SLA response compliance by priority</h2>
{table(["Priority", "Met", "Total", "Rate %", ""],
       [(k, v["met"], v["total"], v["rate_pct"], "") for k, v in sla["by_priority"].items()])}
<h2>SLA response compliance by channel</h2>
{table(["Channel", "Met", "Total", "Rate %"],
       [(k, v["met"], v["total"], v["rate_pct"]) for k, v in sla["by_channel"].items()])}
<h2>SLA breaches by priority</h2>
{table(["Priority", "Breaches"], list(m["breaches_by_priority"].items()))}
<h2>Routing</h2>
{table(["Metric", "Value"], [(k, v) for k, v in m["routing"].items()])}
<h2>Ticket status</h2>
{table(["Status", "Tickets"], list(m["status"].items()))}
<h2>Most loaded agents (active vs capacity)</h2>
{table(["Agent", "Active", "Capacity"],
       [(a["agent_id"], a["active"], a["capacity"]) for a in m["utilisation"]["top_loaded"]])}
<h2>Anomaly detection vs ground truth</h2>
{table(["Type", "TP", "FP", "FN", "Precision", "Recall", "F1"],
       [(k, v["tp"], v["fp"], v["fn"], v["precision"], v["recall"], v["f1"]) for k, v in evaluation.items()])}
</body></html>"""
(out_dir / "dashboard.html").write_text(html, encoding="utf-8")
print("Wrote", out_dir / "dashboard.html")