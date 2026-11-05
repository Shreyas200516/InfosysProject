
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
SPLIT_DIR = BASE_DIR / "dataset" / "splits"

files = {
    "type_train.csv": 3200,
    "type_test.csv": 800,
    "priority_train.csv": 3200,
    "priority_test.csv": 800
}

all_ok = True

for filename, expected_rows in files.items():
    path = SPLIT_DIR / filename

    if not path.exists():
        print(f"MISSING: {filename}")
        all_ok = False
        continue

    df = pd.read_csv(path)
    correct = len(df) == expected_rows

    print(
        f"{filename}: {len(df)} rows | "
        f"Expected: {expected_rows} | "
        f"{'PASS' if correct else 'FAIL'}"
    )

    if not correct:
        all_ok = False

print("\nFinal result:",
      "ALL CHECKS PASSED" if all_ok else "CHECK FAILED")