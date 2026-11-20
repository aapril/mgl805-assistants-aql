"""Agent 7: written summary, with a separate deterministic recommendation."""
from .common import analyze


def run(context, model, results):
    result = analyze(model, 7,
        "Summarize the six analyses: priority risks, concrete actions, and uncertainties. "
        "Do not create new findings; leave findings and criteria empty. "
        "Never declare a merge approved. The program will compute the recommendation.",
        {"agents": [r.model_dump() for r in results], "warnings": context.warnings})
    result.findings = []
    result.criteria = []
    return result


def recommendation(context, results):
    changes, missing = [], []
    if context.demo:
        missing.append("Simulated demonstration: no real review.")
    for r in results:
        if r.status != "complete":
            missing.append(f"Agent {r.agent} incomplete.")
        if any(f.severity in ("high", "critical")
               and f.grounded != "absent"
               for f in r.findings):
            changes.append(
                f"Major finding from agent {r.agent}"
                " to verify and correct.")
        if any(f.grounded == "absent" for f in r.findings):
            missing.append(
                f"Agent {r.agent}: evidence not found"
                " in the diff or issue; check it.")
        if any(f.grounded == "issue_only" for f in r.findings):
            missing.append(
                f"Agent {r.agent}: cites names found in the"
                " issue but not in the diff; check that"
                " they are implemented.")
    compliance = next((r for r in results if r.agent == 4), None)
    if not compliance or not compliance.criteria or any(c.status == "unknown" for c in compliance.criteria):
        missing.append("Acceptance criteria missing or partly unknown.")
    if compliance and any(c.status == "not_met" for c in compliance.criteria):
        changes.append("At least one criterion appears not to be met.")
    evidence = context.evidence
    for name in ("ruff", "pytest", "bandit", "gitleaks"):
        tool = evidence.tools.get(name) if evidence else None
        if not tool or tool.status in ("error", "not_run"):
            missing.append(f"Evidence from {name} missing or unusable.")
        elif tool.status == "failed" or tool.total_findings > 0 or tool.findings:
            changes.append(f"Check {name} reported deviations.")
    if not evidence or evidence.coverage_percent is None:
        missing.append("Coverage unknown.")
    elif evidence.coverage_percent < 80:
        changes.append("Line coverage below the 80% teaching threshold.")
    if not evidence or evidence.tests_run - evidence.tests_skipped <= 0:
        missing.append("No test actually executed.")
    if evidence and evidence.tests_failed:
        changes.append("Some tests failed.")
    if context.warnings:
        missing.extend(context.warnings)
    if changes:
        return "changes_recommended", changes + missing
    if missing:
        return "human_review_required", missing
    return "ready_for_human_approval", [
        "Available checks satisfied; "
        "human approval is mandatory."]
