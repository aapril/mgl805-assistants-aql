"""Reports: Markdown for people, JSON for the evaluation kit and the audit."""
from pathlib import Path

MARK = {"artifact": " (found in the artifact)", "reference_only": " (found in the REFERENCE ONLY)",
        "absent": " (NOT FOUND)", None: ""}


def markdown(report):
    lines = [f"# {report.assistant}", "", f"Run `{report.run_id}` · model `{report.model}`",
             f"Artifact digest `{report.artifact_digest[:16]}…`", "",
             f"**Recommendation: {report.decision}**", "",
             "A person verifies the evidence and makes the decision.", "", "## Reasons", ""]
    lines += [f"- {r}" for r in report.reasons] + ["", "## Deterministic tools", ""]
    lines += [f"- {t.name}: {t.status}" for t in report.tools] or ["- none"]
    for r in report.results:
        lines += ["", f"## Agent {r.agent} ({r.status})", "", r.summary, ""]
        for c in r.criteria:
            lines.append(f"- {c.id} [{c.status}] {c.text}" + (f" — evidence: {c.evidence}" if c.evidence else ""))
        for f in r.findings:
            lines += [f"- **{f.severity}: {f.title}** ({f.source})",
                      f"  Evidence{MARK[f.grounded]}: {f.evidence}", f"  Action: {f.recommendation}"]
        lines += [f"- Limitation: {x}" for x in r.limitations]
    return "\n".join(lines) + "\n"


def save(report, root="runs"):
    folder = Path(root) / report.run_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (folder / "report.md").write_text(markdown(report), encoding="utf-8")
    return folder
