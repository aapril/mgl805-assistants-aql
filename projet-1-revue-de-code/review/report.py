"""Generate Markdown and JSON review reports."""
from pathlib import Path
from .security import safe_markdown as safe


GROUNDING = {"diff": " (found in the diff)", "issue_only": " (found in the ISSUE ONLY, not in the diff)",
             "absent": " (NOT FOUND in the diff or issue)", None: ""}


def markdown(review):
    lines = ["# Code Review Report", "", f"Run: `{review.run_id}`", "",
        f"Repository: {safe(review.repository)} · PR {review.pr} · GitHub issue #{review.issue_id}", "",
        f"Commit analyzed: `{review.head_sha}`", "",
        f"**Recommendation: {review.decision}**", "",
        "A person must verify the evidence and make the final decision. No automatic merge.", ""]
    if review.demo:
        lines += ["**SIMULATED DEMONSTRATION: no model or analysis tool was run.**", ""]
    lines += ["## Reasons", ""] + ["- " + safe(r) for r in review.reasons] + [""]
    lines += ["## Deterministic Checks", "", "| Tool | Status | Number of findings |", "|---|---|---:|"]
    for name in ("ruff", "pytest", "bandit", "gitleaks"):
        tool = review.tools.get(name)
        lines.append(f"| {name} | {tool.status if tool else 'not_run'} | {tool.total_findings if tool else 'unknown'} |")
    lines += ["", f"Line coverage: {review.coverage_percent if review.coverage_percent is not None else 'unknown'}", ""]
    for result in review.results:
        lines += [f"## Agent {result.agent}", "", f"Status: {result.status}", "", safe(result.summary), ""]
        for f in result.findings:
            location = f"{f.file or 'location not given'}:{f.line or '?'}"
            lines += [f"- **{f.severity} — {safe(f.title)}** ({f.source})", f"  Location: {safe(location)}. Evidence{GROUNDING[f.grounded]}: {safe(f.evidence)}", f"  Action: {safe(f.recommendation)}"]
        if result.criteria:
            lines += ["", "| Criterion | Status | Evidence |", "|---|---|---|"]
            for c in result.criteria:
                values = [safe(c.id + ' ' + c.text), c.status, safe(c.evidence)]
                lines.append("| " + " | ".join(x.replace("\n", " ") for x in values) + " |")
        lines += [""] + ["- Limitation: " + safe(x) for x in result.limitations] + [""]
    return "\n".join(lines)


def save(review, root: Path):
    root.mkdir(parents=True, exist_ok=True)
    dest = root / review.run_id
    dest.mkdir(mode=0o700)
    (dest / "review.json").write_text(review.model_dump_json(indent=2), encoding="utf-8")
    (dest / "report.md").write_text(markdown(review), encoding="utf-8")
    return dest


def publication_text(review):
    from .connectors import COMMENT_MARKER
    lines = [
        COMMENT_MARKER, "## AI Review: Seven Agents", "",
        f"GitHub issue: #{review.issue_id} · Commit: `{review.head_sha}`", "",
        f"**Recommandation : {review.decision}**", "",
        "Human approval is mandatory. No automatic merge.", "",
    ]
    if review.demo:
        lines += ["**Simulation without a real model.**", ""]
    lines += ["### Reasons", ""] + ["- " + safe(x) for x in review.reasons[:12]]
    lines += ["", "### Agents", ""]
    for result in review.results:
        lines.append(
            f"- **Agent {result.agent}**: {result.status}, "
            f"{safe(result.summary)}"
        )
        for finding in result.findings[:3]:
            lines.append(f"  - {finding.severity}: {safe(finding.title)} ({safe(finding.file or 'file not given')})")
    lines += ["", "The full report (Markdown and JSON) is available in the artifacts of this GitHub Actions run."]
    return "\n".join(lines)[:55_000]
