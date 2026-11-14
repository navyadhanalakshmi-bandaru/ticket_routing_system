"""Generate the dataset twice and report the first difference per table."""
from generator.generate import generate_dataset


def flatten(master, supporting, transactions):
    tables = {}
    for group in (master, supporting, transactions):
        for name, rows in group.items():
            if isinstance(rows, list):
                tables[name] = rows
    return tables


a = flatten(*generate_dataset())
b = flatten(*generate_dataset())

all_same = True
for name in sorted(set(a) | set(b)):
    ra, rb = a.get(name, []), b.get(name, [])
    if len(ra) != len(rb):
        print(f"{name}: row count differs {len(ra)} vs {len(rb)}")
        all_same = False
        continue
    for i, (x, y) in enumerate(zip(ra, rb)):
        if x != y:
            diff = {k: (x.get(k), y.get(k)) for k in x if x.get(k) != y.get(k)}
            print(f"{name}: first difference at row {i}: {diff}")
            all_same = False
            break
    else:
        print(f"{name}: identical ({len(ra)} rows)")

print("\nRESULT:", "IDENTICAL" if all_same else "DIFFERENT")