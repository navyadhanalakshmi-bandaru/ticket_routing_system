"""Compares detector output with ground truth: TP / FP / FN, precision, recall, F1."""
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anomaly_detector import DEFAULT_DB_PATH, run_all_detectors

report_dir = Path(DEFAULT_DB_PATH).parent / "reports"
findings = run_all_detectors(report_path=report_dir / "anomalies_detected.csv")

conn = sqlite3.connect(DEFAULT_DB_PATH)
truth = {(t, s) for t, s in conn.execute("SELECT ticket_id, scenario_name FROM anomaly_labels")}
conn.close()
detected = {(f["ticket_id"], f["issue_type"]) for f in findings}


def scores(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return round(precision, 4), round(recall, 4), round(f1, 4)


types = sorted({s for _, s in truth} | {i for _, i in detected})
result = {}
print(f"{'type':36} {'TP':>4} {'FP':>6} {'FN':>4}  precision recall   f1")
for kind in types:
    t = {x for x in truth if x[1] == kind}
    d = {x for x in detected if x[1] == kind}
    tp, fp, fn = len(t & d), len(d - t), len(t - d)
    p, r, f = scores(tp, fp, fn)
    result[kind] = dict(tp=tp, fp=fp, fn=fn, precision=p, recall=r, f1=f)
    print(f"{kind:36} {tp:>4} {fp:>6} {fn:>4}  {p:>9} {r:>6} {f:>6}")

tp, fp, fn = len(truth & detected), len(detected - truth), len(truth - detected)
p, r, f = scores(tp, fp, fn)
result["OVERALL"] = dict(tp=tp, fp=fp, fn=fn, precision=p, recall=r, f1=f)
print(f"\nOVERALL TP={tp} FP={fp} FN={fn} precision={p} recall={r} f1={f}")

samples = defaultdict(list)
for ticket_id, kind in sorted(detected - truth):
    samples[kind].append(ticket_id)
for kind, ids in samples.items():
    print(f"\nFalse positives for {kind}: {len(ids)} e.g. {ids[:5]}")

(report_dir / "anomaly_evaluation.json").write_text(json.dumps(result, indent=2))
print(f"\nSaved {report_dir / 'anomalies_detected.csv'} and anomaly_evaluation.json")