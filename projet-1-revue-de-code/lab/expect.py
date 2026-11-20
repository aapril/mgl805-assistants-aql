"""Compares fields of a normalized evidence file with the values printed in the book.

Usage: python lab/expect.py evidence.json key=value [key=value ...]
Keys: pytest (details), coverage, ruff, bandit, gitleaks (status).
"""
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
actual = {
    "pytest": data["tools"]["pytest"]["details"],
    "coverage": str(data["coverage_percent"]),
    **{t: data["tools"][t]["status"] for t in ("ruff", "bandit", "gitleaks")},
}
failed = False
for pair in sys.argv[2:]:
    key, expected = pair.split("=", 1)
    if actual[key] != expected:
        print(f"  {key}: expected {expected!r}, got {actual[key]!r}")
        failed = True
sys.exit(1 if failed else 0)
