import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anomaly_detector import DEFAULT_DB_PATH

db = sqlite3.connect(DEFAULT_DB_PATH)
tables = [r[0] for r in db.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
out = ["# Data dictionary", "",
       "Generated from the SQLite schema by scripts/make_data_dictionary.py.",
       "All data is synthetic (seed in config/settings.py); no external or personal data is used.", ""]
relations = []
for t in tables:
    rows = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    fks = {r[3]: f"{r[2]}.{r[4]}" for r in db.execute(f"PRAGMA foreign_key_list({t})")}
    for col, target in fks.items():
        relations.append(f"- {t}.{col} -> {target} (N:1)")
    out += [f"## {t} ({rows} rows)", "",
            "| Column | Type | Required | Key | Allowed values / example |", "|---|---|---|---|---|"]
    for _, name, typ, notnull, _, pk in db.execute(f"PRAGMA table_info({t})"):
        key = "PK (unique)" if pk else (f"FK -> {fks[name]}" if name in fks else "")
        vals = [str(r[0]) for r in db.execute(f"SELECT DISTINCT {name} FROM {t} LIMIT 13")]
        shown = ", ".join(vals) if len(vals) <= 12 else f"e.g. {vals[0]}"
        out.append(f"| {name} | {typ} | {'yes' if notnull or pk else 'no'} | {key} | {shown.replace('|', '/')} |")
    out.append("")
out += ["## Relationships (foreign keys)", ""] + relations
Path("docs").mkdir(exist_ok=True)
Path("docs/data_dictionary.md").write_text("\n".join(out), encoding="utf-8")
print("Wrote docs/data_dictionary.md")