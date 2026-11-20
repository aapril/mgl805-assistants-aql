"""Quality gates: the oracle, written by people, evaluated by rules.

A gate whose metric could not be measured on the whole repository (a file
skipped or impossible to parse, or no layer rules for ARCH-1) is neither met
nor failed: it is not measured, and a person must decide.
"""
from .contracts import GateResult


def value(metric, m):
    count = lambda kind: sum(1 for v in m.violations if v.kind == kind)
    return {"layer_violations": count("layer"), "cycles": len(m.cycles),
            "max_complexity": max((f.complexity for f in m.functions), default=0),
            "max_function_lines": max((f.length for f in m.functions), default=0),
            "duplication_pct": m.duplication_pct, "debt_ratio_pct": m.debt_ratio_pct,
            "markers": len(m.markers)}[metric]


def evaluate(gates, m, rules):
    incomplete = bool(m.skipped or m.parse_errors)
    unassigned = [x.name for x in m.modules if x.layer is None and "." in x.name]
    results = []
    for g in gates:
        v = value(g["metric"], m)
        partial = incomplete or (g["metric"] == "layer_violations" and (not rules.get("layers") or bool(unassigned)))
        if v > g["max"]:
            status = "not_met"  # a violation found in the measured part is real
        elif partial:
            status = "not_measured"  # a pass on part of the code proves nothing about the rest
        else:
            status = "met"
        results.append(GateResult(id=g["id"], text=g["text"], metric=g["metric"], status=status, measured=v, threshold=g["max"]))
    return results
