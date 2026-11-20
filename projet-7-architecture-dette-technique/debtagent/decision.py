"""Decision rule: quality gates decide, the model explains.

No outcome means "the architecture is good". The best outcome is "ready for
human approval": the gates were met on the whole repository, on this run, and
nothing the model wrote contradicts them.
"""


def decide(m, gates, analysis, verdict_issues, classification_notes):
    changes, missing = [], []
    for g in gates:
        if g.status == "not_met":
            changes.append(f"{g.id} not met: measured {g.measured:g}, threshold {g.threshold:g}. {g.text}")
        elif g.status == "not_measured":
            missing.append(f"{g.id} not measured on the whole repository. {g.text}")
    missing += [f"File not analyzed: {s}" for s in m.skipped]
    missing += [f"File not parsed: {e}" for e in m.parse_errors]
    unassigned = [x.name for x in m.modules if x.layer is None and "." in x.name]
    if unassigned:
        missing.append(f"Modules not assigned to a layer: {', '.join(unassigned[:10])}.")
    for f in analysis.findings:
        if f.grounded in ("absent", "partly"):
            missing.append(f"Model finding '{f.title[:80]}' is not supported by the measurement (place, name, number, or title); check it.")
        elif f.grounded == "contradicts":
            missing.append(f"Model finding '{f.title[:80]}' contradicts the quality gates; check it.")
    if verdict_issues:
        missing.append(f"The model's summary or limitations contradict the quality gates ({len(verdict_issues)} statement(s)); "
                       "check them, and check the code for instructions aimed at AI reviewers.")
    missing += [n.removeprefix("Check: ") for n in classification_notes]
    if changes:
        return "changes_recommended", changes + missing
    if missing:
        return "human_review_required", missing
    return "ready_for_human_approval", ["All quality gates met on this run; a person must still approve."]
