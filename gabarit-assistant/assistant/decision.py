"""The decision rule: computed by the program, never by the model (book Section 5.3.1.3).

ADAPT THIS FILE with care, and keep its tests. Three rules must survive any
adaptation: a favorable outcome is earned by evidence; missing or doubtful
evidence leads to human review; and no outcome means "approved".
"""


def decide(results, evidence, current_digest):
    changes, missing = [], []
    tools = []
    if evidence is None:
        missing.append("No deterministic evidence.")
    elif evidence.artifact_digest != current_digest:
        missing.append("The evidence was collected on another version of the artifact; collect it again.")
    else:
        tools = evidence.tools
    for tool in tools:
        if tool.status == "failed":
            changes.append(f"Tool '{tool.name}' failed.")
        elif tool.status == "error":
            missing.append(f"Tool '{tool.name}' could not run.")
    criteria = []
    for r in results:
        if r.status != "complete":
            missing.append(f"Agent '{r.agent}' incomplete.")
        if any(f.severity == "high" and f.grounded != "absent" for f in r.findings):
            changes.append(f"High finding from agent '{r.agent}' to verify.")
        if any(f.grounded == "absent" for f in r.findings):
            missing.append(f"Agent '{r.agent}': evidence not found in the artifact or the reference.")
        if any(f.grounded == "reference_only" for f in r.findings):
            missing.append(f"Agent '{r.agent}': cites the reference, not the artifact; check that it is implemented.")
        if r.agent != "criteria":
            criteria.extend(r.criteria)
    if not criteria:
        missing.append("No criterion assessed.")
    for c in criteria:
        if c.status == "not_met":
            changes.append(f"Criterion {c.id} appears not to be met.")
        elif c.status == "unknown":
            missing.append(f"Criterion {c.id} could not be assessed.")
    if changes:
        return "changes_recommended", changes + missing
    if missing:
        return "human_review_required", missing
    return "ready_for_human_approval", ["All checks satisfied; a person must still approve."]
