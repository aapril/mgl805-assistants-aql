"""Decision rule: the log and the evidence decide, the model drafts.

"regressions_found" means that errors appeared after the last deployment and
were never seen before it; each comes with its attribution, from the program.
No outcome closes a bug or confirms a cause: a person does.
"""

LABEL = {"confirmed": "cause confirmed by reproduction", "probable": "probable cause, not reproduced",
         "uncertain": "cause uncertain", "pre_existing": "existed before the deployment"}


def decide(ev, drafts, verdict_issues):
    regressions, review = [], []
    tri = {t.signature_id: t for t in ev.triage}
    for s in ev.signatures:
        t = tri[s.id]
        where = f"{s.frames[-1].file}:{s.frames[-1].line}" if s.frames else "no traceback"
        top = t.candidates[0] if t.candidates else None
        cause = f"; {LABEL[t.attribution]}" + (f": {top.short} \"{top.subject}\"" if top and t.attribution in ("confirmed", "probable") else "")
        line = f"{s.id} {s.exception or s.level} at {where}, {s.count_after_deploy} time(s) after {ev.deploy_ref}{cause}."
        if t.status == "new_since_deploy" and s.level != "WARNING":
            regressions.append(line)
            if t.attribution == "uncertain":
                review.append(f"{s.id}: no single commit is supported by the evidence; a person must investigate.")
        elif t.status == "unknown":
            review.append(f"{s.id}: cannot tell whether it is new ({t.notes[0] if t.notes else ''})")
        if s.suspicious:
            review.append(f"{s.id}: the log contains text addressed to an AI ({'; '.join(s.suspicious)[:120]}); treat it as untrusted input.")
    for r in drafts.reports:
        if r.grounded in ("absent", "partly"):
            review.append(f"Draft '{r.title[:70]}' is not supported by the evidence; check it.")
        elif r.grounded == "contradicts":
            review.append(f"Draft '{r.title[:70]}' contradicts the evidence; check it.")
    if verdict_issues:
        review.append(f"The model's summary or limitations contradict the log ({len(verdict_issues)} statement(s)); "
                      "check them, and check the log for instructions aimed at AI assistants.")
    if ev.execution != "allowed":
        review.append(f"Reproductions not run ({ev.execution}).")
    if regressions:
        return "regressions_found", regressions + review
    if review:
        return "human_review_required", review
    return "no_new_errors", [f"No new error since {ev.deploy_ref}; a person must still approve."]
