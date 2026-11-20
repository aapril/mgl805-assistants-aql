"""Decision rule: requirements decide, the model explains.

No outcome means "the application is fast enough". The best outcome is
"ready for human approval": the measured requirements were met at the load
they specify, in this environment, on this run.
"""


def decide(measurement, slos, analysis, adjustments):
    changes, missing = [], []
    if measurement is None:
        missing.append("No measurement: the load test did not run.")
    elif measurement.total_requests == 0:
        missing.append("The load test sent no request.")
    for s in slos:
        if s.status == "not_met":
            changes.append(f"{s.id} not met: measured {s.measured}, threshold {s.threshold}. {s.text}")
        elif s.status == "not_measured":
            missing.append(f"{s.id} not measured at the required load. {s.text}")
    if adjustments:
        missing.extend(f"Scenario adjusted by the safety limits: {a}" for a in adjustments)
    for f in analysis.findings:
        if f.grounded in ("absent", "partly"):
            missing.append(f"Model finding '{f.title[:80]}' cites values that were not measured; check it.")
        elif f.grounded == "contradicts":
            missing.append(f"Model finding '{f.title[:80]}' contradicts the measured requirements; check it.")
    if changes:
        return "changes_recommended", changes + missing
    if missing:
        return "human_review_required", missing
    return "ready_for_human_approval", ["All performance requirements met on this run; a person must still approve."]
