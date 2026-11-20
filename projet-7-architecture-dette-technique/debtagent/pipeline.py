"""Fixed order: measure, evaluate, classify, explain, ground, decide."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import gates as gates_mod
from . import grounding, measure
from .contracts import Analysis, Classification, Report
from .decision import decide


def excerpts(repo, m, limits):
    """Numbered source of the modules that carry the most debt, as data for the analyst."""
    cost = {}
    for v in m.violations:
        module = v.location.split(":")[0]
        cost[module] = cost.get(module, 0) + v.remediation_min
    paths = {x.name: x.path for x in m.modules}
    out = []
    for module in sorted(cost, key=lambda k: -cost[k])[: limits["excerpts"]]:
        lines = (Path(repo) / paths[module]).read_text(encoding="utf-8", errors="replace").splitlines()
        body = "\n".join(f"{i:4} {l}" for i, l in enumerate(lines[: limits["excerpt_lines"]], 1))
        out.append({"module": module, "path": paths[module], "code": body})
    return out


def run(repo, rules, architecture, model):
    m = measure.run(repo, rules)  # the code is parsed, never imported or run
    results = gates_mod.evaluate(rules["gates"], m, rules)
    failure = []
    try:
        classification = model.classify({"markers": [mk.model_dump() for mk in m.markers]}) if m.markers else Classification()
    except Exception as exc:  # noqa: BLE001 - a failed classification never hides the measurement
        classification = Classification()
        failure = [f"Check: marker classification not completed: {type(exc).__name__}."]
    notes = failure + grounding.check_classification(classification, m)
    payload = {"architecture": architecture, "quality_gates": [g.model_dump() for g in results],
               "violations": [v.model_dump() for v in m.violations[:60]],
               "most_complex_functions": [f.model_dump() for f in m.functions[:10]],
               "modules": [x.model_dump() for x in m.modules], "cycles": m.cycles,
               "debt": {"remediation_min": m.remediation_min, "debt_ratio_pct": m.debt_ratio_pct,
                        "duplication_pct": m.duplication_pct, "total_lines": m.total_lines},
               "marker_types": [c.model_dump() for c in classification.items],
               "code_excerpts": excerpts(repo, m, rules["limits"])}
    try:
        analysis = model.analyze(payload)
    except Exception as exc:  # noqa: BLE001 - a failed explanation never hides the measurement
        analysis = Analysis(summary="Analysis not completed.",
                            limitations=[f"Failure {type(exc).__name__}: {str(exc)[:200]}"])
    verdict_issues = grounding.check(analysis, m, results)
    decision, reasons = decide(m, results, analysis, verdict_issues, notes)
    return Report(run_id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(), model=model.name,
                  measurement=m, gates=results, classification=classification, analysis=analysis,
                  decision=decision, reasons=reasons)
