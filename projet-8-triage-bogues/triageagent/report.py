"""Reports: Markdown for people, JSON for evaluation and audit."""
from pathlib import Path

MARK = {"measured": " (names found in the evidence)", "partly": " (SOME NAMES NOT IN THE EVIDENCE)",
        "absent": " (NOT FOUND in the evidence)", "contradicts": " (CONTRADICTS the evidence)", None: ""}
PATCH = {"applies": "applies to the deployed code (not applied)", "does_not_apply": "DOES NOT APPLY to the deployed code",
         "none": "none", "not_checked": "not checked", None: "not checked"}


def markdown(r):
    ev, tri = r.evidence, {t.signature_id: t for t in r.evidence.triage}
    lines = ["# Bug triage report", "", f"Run `{r.run_id}` · model `{r.model}` · log `{ev.log}` · repository `{ev.repo}`", "",
             f"**Recommendation: {r.decision}**", "", "A person confirms each cause and each patch.", "",
             "## Reasons", ""] + [f"- {x}" for x in r.reasons]
    lines += ["", "## Deployment", "",
              (f"Deployed `{ev.deploy_ref}` ({(ev.deploy_sha or 'unknown')[:7]}) at {ev.deploy_time}; previous deployment `{ev.previous_ref}`. "
               f"Reproductions: {ev.execution}."), "", "| Commit | Date | Subject | Files |", "|---|---|---|---|"]
    lines += [f"| {c.short} | {c.date[:10]} | {c.subject} | {', '.join(c.files)} |" for c in ev.window]
    lines += ["", "## Signatures", "", "| Id | Level | Problem | Innermost frame | Before | After | Status | Attribution |",
              "|---|---|---|---|---:|---:|---|---|"]
    for s in ev.signatures:
        t = tri[s.id]
        frame = f"{s.frames[-1].file}:{s.frames[-1].line}" if s.frames else "n/a"
        problem = s.message.replace("|", "/")
        lines.append(f"| {s.id} | {s.level} | {problem} | {frame} | {s.count_before_deploy} | {s.count_after_deploy} | {t.status} | {t.attribution} |")
    for s in ev.signatures:
        t = tri[s.id]
        lines += ["", f"### {s.id} · {s.exception or s.level}", "", f"First seen {s.first_seen}, last seen {s.last_seen}, {s.count} time(s)."]
        if s.suspicious:
            lines.append(f"**Untrusted text addressed to an AI in this log entry:** {'; '.join(s.suspicious)}.")
        for c in t.candidates:
            lines.append(f"- Candidate {c.short} \"{c.subject}\" (score {c.score}): {'; '.join(c.evidence)}.")
        lines += [f"- Note: {n}" for n in t.notes]
        if t.reproduction:
            x = t.reproduction
            lines.append(f"- Reproduction `{' '.join(x.command)}`: {x.at_commit} at {x.commit[:7]}, {x.at_parent} at its parent "
                         f"{x.parent[:7]}: **{x.verdict}**.")
    lines += ["", "## Draft bug reports (model)", "", r.drafts.summary, ""]
    for b in r.drafts.reports:
        lines += [f"- **{b.severity}: {b.title}** ({b.signature_id}; suspected commit {b.suspected_commit or 'none'})",
                  f"  Explanation{MARK[b.grounded]}: {b.explanation}", f"  Patch: {PATCH[b.patch_status]}"]
        if b.suggested_patch.strip():
            lines += ["", "```diff", b.suggested_patch.rstrip(), "```", ""]
        if b.next_steps:
            lines.append(f"  Next steps: {b.next_steps}")
    lines += [f"- Program check: {x.removeprefix('Check: ')}" if x.startswith("Check: ") else f"- Model limitation: {x}"
              for x in r.drafts.limitations]
    return "\n".join(lines) + "\n"


def save(report, root="runs"):
    folder = Path(root) / report.run_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (folder / "report.md").write_text(markdown(report), encoding="utf-8")
    return folder
