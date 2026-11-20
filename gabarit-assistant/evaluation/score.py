"""Scores an assistant built from the template against a corpus of seeded defects (book Section 5.4.5).

extract: turns one review.json into a judgment sheet that a human reviewer fills in;
score:   computes precision, recall, and F1 from the filled sheets.

In the judgment sheet, each row is one finding of the AI reviewer. The human
reviewer writes TP in the verdict column when the finding is correct and useful,
FP when it is wrong or unjustified, and, for a TP, the identifier of the seeded
defect it reveals (D1, D2, ...) in matched_defect, or NEW for a real defect that
was not seeded. Leave nothing blank: an unjudged finding stops the scoring.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

FIELDS = ["case", "run_id", "agent", "finding", "severity", "grounded", "title", "verdict", "matched_defect"]


def extract(review_path, case, out):
    review = json.loads(Path(review_path).read_text(encoding="utf-8"))
    rows = []
    for result in review["results"]:
        for n, f in enumerate(result["findings"], 1):
            rows.append({"case": case, "run_id": review["run_id"], "agent": result["agent"],
                         "finding": f"{result['agent']}.{n}", "severity": f["severity"],
                         "grounded": f.get("grounded") or "", "title": f["title"],
                         "verdict": "", "matched_defect": ""})
    with open(out, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} findings written to {out}; fill in verdict and matched_defect.")


def score(defects_path, sheets):
    seeded = defaultdict(set)
    with open(defects_path, newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            seeded[row["case"]].add(row["defect_id"])
    tp = fp = 0
    found = defaultdict(set)
    judged = set()
    for sheet in sheets:
        with open(sheet, newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                judged.add(row["case"])
                verdict = row["verdict"].strip().upper()
                if verdict not in ("TP", "FP"):
                    sys.exit(f"{sheet}: finding {row['finding']} has no verdict (TP or FP).")
                if verdict == "FP":
                    fp += 1
                    continue
                tp += 1
                defect = row["matched_defect"].strip().upper()
                if defect and defect != "NEW":
                    if defect not in seeded[row["case"]]:
                        sys.exit(f"{sheet}: {defect} is not a seeded defect of case {row['case']}.")
                    found[row["case"]].add(defect)
    # Recall is computed only over the cases that were actually reviewed and judged.
    cases = sorted(judged)
    unknown = [c for c in cases if c not in seeded]
    if unknown:
        sys.exit(f"Cases without seeded defects: {', '.join(unknown)}")
    total_seeded = sum(len(seeded[c]) for c in cases)
    total_found = sum(len(found[c]) for c in cases)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = total_found / total_seeded if total_seeded else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    for c in cases:
        missed = sorted(seeded[c] - found[c])
        print(f"{c}: {len(found[c])}/{len(seeded[c])} seeded defects found; missed: {', '.join(missed) or 'none'}")
    print(f"Findings judged: {tp + fp} (TP {tp}, FP {fp})")
    print(f"Precision = {precision:.2f}  Recall = {recall:.2f}  F1 = {f1:.2f}")
    return precision, recall, f1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    e = sub.add_parser("extract")
    e.add_argument("review", type=Path)
    e.add_argument("--case", required=True)
    e.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("score")
    s.add_argument("--defects", type=Path, default=Path(__file__).with_name("seeded_defects.csv"))
    s.add_argument("sheets", type=Path, nargs="+")
    args = parser.parse_args()
    if args.command == "extract":
        extract(args.review, args.case, args.out)
    else:
        score(args.defects, args.sheets)


if __name__ == "__main__":
    main()
