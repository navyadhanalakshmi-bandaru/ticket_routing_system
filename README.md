# Ticket Routing System

## Setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

## Run order (from a clean checkout)
Remove-Item outputs\ticket_routing_generated.db   # only if it already exists
python -m generator.generate        # deterministic dataset; runs twice and compares checksums
python scripts\fix_baseline.py      # calendar-based SLA targets + capacity-aware assignment
python scripts\evaluate_anomalies.py
python scripts\build_report.py      # outputs\reports\dashboard.html
python -m pytest -v

## Components
- generator/: synthetic data, workload normalisation, five injected labelled anomalies
- services/routing_engine.py: skill, language, shift and capacity-aware routing
- services/sla_engine.py: calendar-aware SLA deadlines, breach and escalation logic
- services/anomaly_detector.py: five detectors that never read ground truth
- services/metrics.py, scripts/build_report.py: metrics and static HTML dashboard

## Results
- Anomaly detection vs ground truth: precision, recall and F1 = 1.0 on all five types.
- Generator checksum identical across runs (534215e7...3240); the post-fix DB hash is also identical across two clean runs.
- 15 tests pass.

## Notes
- The generated DB and the CSV/JSON exports are git-ignored. Run the pipeline above to recreate them.

## Known limitations
- fix_baseline.py is a post-process. The generator itself emits elapsed-time SLA targets and random agent assignment, so run fix_baseline.py after every generate. Moving this into generate.py is future work.
- response_met SLA events keep their original target_at.
- Reassignment only uses agents already seen on the same queue.