"""Agent 5: analyzes the test evidence; it never runs PR code."""
from .common import analyze, code_payload


def run(context, model, requirements):
    payload = code_payload(context)
    payload["criteria"] = [{"id": c.id, "text": c.text} for c in requirements.criteria]
    payload["test_evidence"] = context.evidence.model_dump() if context.evidence else None
    return analyze(model, 5,
        "Assess the visible test cases and propose precise nominal, boundary, and error cases. "
        "The only tests that were run are those in the supplied report, which is tied to the commit. "
        "Missing coverage is unknown, never 100%. Line coverage does not prove business conformance. "
        "Never present your proposals as executed. "
        "Passing tests do not prove that the new features are tested. "
        "Distinguish executed tests from missing or proposed tests. "
        "pytest results give numbers of tests, not necessarily the cases tested. "
        "Never conclude that a specific function was tested only because pytest passed.",
        payload)
