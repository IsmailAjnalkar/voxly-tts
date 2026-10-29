"""Compute the readiness score from audit/TEST_CASE_MATRIX.csv.
PASS=1, PARTIAL=0.5, FAIL=0. Tested score uses tested cases only; readiness
score also counts NOT TESTED/BLOCKED as 0. N/A and NOT IMPLEMENTED are excluded."""
import csv
import sys
from collections import defaultdict
from pathlib import Path

WEIGHTS = {"CORE": 25, "AUDIO": 10, "UI": 10, "API": 10, "SEC": 15,
           "PERF": 10, "AUTH": 5, "A11Y": 5, "SEO": 5, "TEST": 5}
CREDIT = {"PASS": 1, "PARTIAL": 0.5, "FAIL": 0}

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parents[1] / "TEST_CASE_MATRIX.csv"
rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
bad = [r["TC_ID"] for r in rows if None in r or r["Dimension"] not in WEIGHTS]
assert not bad, f"malformed rows: {bad}"

d = defaultdict(lambda: defaultdict(int))
for r in rows:
    d[r["Dimension"]][r["Status"]] += 1

tested_total = ready_total = 0
print(f"{'Dim':6} {'W':>3} {'Appl':>4} {'Test':>4} {'Pass':>4} {'Part':>4} {'Fail':>4} {'Blk/NT':>6} {'Tested':>7} {'Ready':>6}")
for dim, w in WEIGHTS.items():
    c = d[dim]
    tested = c["PASS"] + c["PARTIAL"] + c["FAIL"]
    untested = c["NOT TESTED"] + c["BLOCKED"]
    credit = sum(c[k] * v for k, v in CREDIT.items())
    t = w * credit / tested if tested else 0
    rd = w * credit / (tested + untested) if tested + untested else 0
    tested_total += t
    ready_total += rd
    print(f"{dim:6} {w:>3} {tested + untested:>4} {tested:>4} {c['PASS']:>4} {c['PARTIAL']:>4} {c['FAIL']:>4} {untested:>6} {t:>7.2f} {rd:>6.2f}")

applicable = sum(1 for r in rows if r["Status"] not in ("NOT APPLICABLE", "NOT IMPLEMENTED"))
tested_n = sum(1 for r in rows if r["Status"] in CREDIT)
print(f"\nTOTAL tested-score {tested_total:.1f}/100 | readiness-score {ready_total:.1f}/100 | "
      f"coverage {tested_n}/{applicable} = {100 * tested_n / applicable:.1f}%")
print("status counts:", {k: sum(1 for r in rows if r['Status'] == k) for k in
                         ["PASS", "PARTIAL", "FAIL", "BLOCKED", "NOT TESTED", "NOT IMPLEMENTED", "NOT APPLICABLE"]})
sys.exit(0)
