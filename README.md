# Intelligent Customer Support Ticket Routing and SLA Management System

An intelligent customer support ticket routing and Service Level Agreement (SLA) management system built with Python, SQLite, Streamlit, and data analytics.

The system routes customer support tickets based on intent, priority, language, agent skills, availability, and workload. It also tracks SLA deadlines using channel-specific business calendars and detects operational anomalies.

All generated data is synthetic. No real customer information is used.

## 1. Project Overview

Customer support teams receive requests through multiple channels, including email, chat, phone, and web.

Manually assigning tickets can cause:
- Delayed responses and SLA violations.
- Incorrect agent assignments.
- Uneven agent workloads.
- Repeated ticket transfers.
- Poor visibility into operational anomalies.

This project addresses these challenges through intelligent ticket routing, SLA monitoring, lifecycle tracking, and anomaly detection.

## 2. Key Features

### Intelligent Ticket Routing
- Routes tickets based on customer intent.
- Matches required agent skills and language proficiency.
- Considers agent availability and working shifts.
- Checks agent workload against concurrent ticket capacity.
- Uses weighted scoring to rank eligible agents.
- Routes tickets to appropriate queues when no eligible agent is available.

### SLA Management
- Calculates response and resolution deadlines.
- Supports channel-specific business calendars.
- Accounts for non-working days and holidays.
- Identifies breached and at-risk tickets.
- Supports escalation levels and priority-based escalation rules.

### Ticket Lifecycle Management
- Tracks ticket status changes.
- Records assignment and transfer events.
- Maintains ticket history.
- Supports resolution and reopening scenarios.
- Records SLA-related events.

### Anomaly Detection

The system detects five labelled anomaly scenarios:

1. Agent over capacity.
2. SLA ignores channel business calendar.
3. Reopened ticket loses lifecycle history.
4. Repeated transfer loop.
5. Ticket priority contradicts safety rules.

Anomaly detection is evaluated separately against labelled ground-truth data.

### Reporting and Analytics
- Ticket volume and status analysis.
- Agent workload analysis.
- SLA performance metrics.
- Anomaly detection results.
- Precision, recall, and F1-score evaluation.
- Generated HTML dashboard and CSV reports.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Database | SQLite |
| Dashboard | Streamlit |
| Data analysis | Pandas, NumPy |
| Visualization | Plotly |
| Synthetic data generation | Faker |
| Machine learning utilities | Scikit-learn |
| Testing | Pytest |

## 4. Architecture

The application follows a three-tier architecture.

### Presentation Layer
- Streamlit dashboard.
- Ticket and agent views.
- SLA monitoring.
- Analytics and reports.

### Application Layer
- Ticket routing engine.
- SLA calculation engine.
- Ticket lifecycle management.
- Anomaly detection.
- Metrics and evaluation.

### Data Layer
- SQLite database.
- Master data and transactional records.
- CSV and JSON exports.
- Ground-truth anomaly labels.

## 5. Dataset Specifications

The synthetic dataset uses a fixed random seed to support reproducibility.

| Dataset | Records |
|---|---:|
| Customers | 10,000 |
| Agents | 100 |
| Tickets | 30,000 |
| Messages | 100,000 |
| Channels | 4 |
| Languages | 7 |
| Intents | 9 |
| Skills | 8 |
| Queues | 6 |

**Dataset period:** 17 August 2026 – 14 November 2026

**Random seed:** `20261022`

The generator performs two generation runs and compares their checksums to verify reproducibility.

## 6. Project Structure

```text
ticket_routing_system/
│
├── config/
│   └── settings.py
│
├── data/
│   ├── database.py
│   └── schema.sql
│
├── generator/
│   ├── generate.py
│   ├── master_data.py
│   ├── transactions.py
│   ├── anomalies.py
│   └── export.py
│
├── services/
│   ├── routing_engine.py
│   ├── sla_engine.py
│   ├── anomaly_detector.py
│   └── metrics.py
│
├── scripts/
│   ├── fix_baseline.py
│   ├── simulate_lifecycle.py
│   ├── finalize_dataset.py
│   ├── evaluate_anomalies.py
│   ├── build_report.py
│   └── make_data_dictionary.py
│
├── validation/
│   ├── data_validator.py
│   └── reproducibility.py
│
├── tests/
│   ├── test_database.py
│   └── test_sla.py
│
├── outputs/
│   ├── final/
│   ├── csv/
│   ├── json/
│   ├── ground_truth/
│   └── reports/
│
├── docs/
│   └── data_dictionary.md
│
├── requirements.txt
└── README.md
```

## 7. Installation

Clone the repository:

```bash
git clone https://github.com/navyadhanalakshmi-bandaru/ticket_routing_system.git
cd ticket_routing_system
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 8. Running the Project

Run the following commands from the project root directory.

### Step 1: Generate the dataset

```bash
python -m generator.generate
```

### Step 2: Prepare the baseline

```bash
python scripts/fix_baseline.py
```

### Step 3: Simulate ticket lifecycle events

```bash
python scripts/simulate_lifecycle.py
```

### Step 4: Finalize the dataset

```bash
python scripts/finalize_dataset.py
```

### Step 5: Evaluate anomaly detection

```bash
python scripts/evaluate_anomalies.py
```

### Step 6: Build the analytics report

```bash
python scripts/build_report.py
```

### Step 7: Run automated tests

```bash
python -m pytest -v
```

**Important:** Run the pipeline in the listed order. If starting from scratch, use a fresh generated database and follow the project's database overwrite safeguards. Do not delete or overwrite a database containing work you need to preserve.

## 9. Outputs

### Final Dataset
`outputs/final/`

Contains finalized CSV exports, SQL seed data, and a manifest containing record counts and file checksums.

### Ground Truth
`outputs/ground_truth/`

Contains labelled anomaly records used for evaluation. Ground-truth labels are kept separate from operational input data.

### Reports
`outputs/reports/`

Contains:
- `anomalies_detected.csv`
- `anomaly_evaluation.json`
- `metrics.json`
- `dashboard.html`

### Documentation
`docs/data_dictionary.md`

Describes database tables, columns, data types, primary keys, and foreign-key relationships.

## 10. Evaluation Metrics

The anomaly detection system is evaluated using:

- True Positives (TP)
- False Positives (FP)
- False Negatives (FN)
- Precision
- Recall
- F1-score

The reported evaluation for the five injected anomaly scenarios:

| Anomaly type | F1-score |
|---|---:|
| Agent over capacity | 1.000 |
| SLA ignores channel calendar | 1.000 |
| Reopened ticket loses history | 1.000 |
| Transfer loop | 1.000 |
| Priority contradicts safety rule | 1.000 |

**Overall reported result:** TP = 5, FP = 0, FN = 0, F1-score = 1.000.

These results apply to the labelled synthetic evaluation dataset, not to independently collected production data.

## 11. Validation and Testing

The project includes validation for:

- Primary-key uniqueness.
- Foreign-key integrity.
- Valid status and priority values.
- Ticket lifecycle consistency.
- Agent skill and language qualification.
- Assignment capacity checks.
- Dataset reproducibility.
- Anomaly detection performance.

Reported validation results:

- Foreign-key violations: 0.
- Final assignment skill/language mismatches: 0.
- Anomaly evaluation false positives: 0.
- Anomaly evaluation false negatives: 0.
- Automated tests: 15 passed.

## 12. Business Rules

1. Required skills are determined by ticket intent.
2. Minimum required skill proficiency is 3.
3. Minimum required language proficiency is 3.
4. Agents must be active and eligible for assignment.
5. Agent workload is checked against configured concurrent capacity.
6. SLA deadlines use the applicable priority policy and channel calendar.
7. Safety-related tickets must have Critical priority.
8. Tickets without eligible agents are placed in an appropriate queue.

## 13. Known Limitations

- The dataset is synthetic and does not represent real customer-support traffic.
- Baseline reopenings are disabled because they previously increased agent workload and produced unintended capacity alerts. The labelled reopened-ticket anomaly remains available for evaluation.
- Baseline transfers are not simulated beyond the injected transfer-loop scenario.
- Agent shift enforcement is performed by the routing engine; the baseline reassignment post-processing step does not enforce shifts.
- First-response timestamps are generated independently of calendar-based SLA deadlines, so measured breach rates are partly influenced by synthetic data generation.
- The holiday calendar is empty in the default generated dataset; holiday handling is covered by unit tests.
- Perfect anomaly detection scores on this controlled dataset should not be interpreted as guaranteed performance on real-world data.

## 14. Future Enhancements

- Integrate live email, chat, and phone support channels.
- Add machine-learning-based ticket intent classification.
- Introduce predictive SLA breach alerts.
- Improve workload forecasting.
- Add real-time agent availability tracking.
- Support additional business calendars and holiday schedules.
- Evaluate anomaly detection on real-world operational datasets.

## 15. Author

Developed as a customer support automation and intelligent ticket management project.

**Repository:**  
https://github.com/navyadhanalakshmi-bandaru/ticket_routing_system

---

*This project demonstrates intelligent ticket assignment, SLA management, synthetic data engineering, anomaly detection, and automated validation using Python.*
