"""Reports: Markdown for people, JSON for evaluation and audit."""
from pathlib import Path

MARK = {"measured": " (numbers found in the measurements)", "partly": " (SOME NUMBERS NOT MEASURED)",
        "absent": " (NOT FOUND in the measurements)",
        "contradicts": " (CONTRADICTS the measured requirements)", None: ""}


def markdown(r):
    m = r.measurement
    lines = [f"# Performance test report", "", f"Run `{r.run_id}` · model `{r.model}`", "",
             f"**Recommendation: {r.decision}**", "", "A person reviews the measurements and decides.", "",
             "## Reasons", ""] + [f"- {x}" for x in r.reasons]
    lines += ["", "## Requirements", "", "| Id | Status | Measured | Threshold |", "|---|---|---:|---:|"]
    lines += [f"| {s.id} | {s.status} | {s.measured if s.measured is not None else 'n/a'} | {s.threshold} |" for s in r.slos]
    lines += ["", "## Scenario", "", f"Proposed by the planner: {r.proposed.name}; {r.proposed.virtual_users} users, {r.proposed.duration_s} s.",
              f"Executed: {r.executed.virtual_users} users, {r.executed.duration_s} s, think time {r.executed.think_time_ms} ms."]
    lines += [f"- Adjustment: {a}" for a in r.adjustments]
    if r.executed.rationale:
        lines += ["", f"Rationale: {r.executed.rationale}"]
    if m:
        lines += ["", "## Measurements", "", f"Target {m.target} · {m.total_requests} requests in {m.elapsed_s} s · "
                  f"{m.throughput_rps} req/s · error rate {m.error_rate:.2%}", "",
                  "| Endpoint | Requests | Errors | p50 ms | p95 ms | p99 ms | max ms |", "|---|---:|---:|---:|---:|---:|---:|"]
        lines += [f"| {e.method} {e.path} | {e.requests} | {e.errors} | {e.p50_ms} | {e.p95_ms} | {e.p99_ms} | {e.max_ms} |" for e in m.endpoints]
    lines += ["", "## Analysis (model)", "", r.analysis.summary, ""]
    for f in r.analysis.findings:
        lines += [f"- **{f.severity}: {f.title}**", f"  Evidence{MARK[f.grounded]}: {f.evidence}", f"  Next step: {f.recommendation}"]
    lines += [f"- Limitation: {x}" for x in r.analysis.limitations]
    return "\n".join(lines) + "\n"


def save(report, root="runs"):
    folder = Path(root) / report.run_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (folder / "report.md").write_text(markdown(report), encoding="utf-8")
    return folder
