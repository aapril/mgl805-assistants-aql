"""Agent 1: turns the GitHub Issue into traceable acceptance criteria."""
from .common import analyze


def run(context, model):
    return analyze(model, 1,
        "Extract the explicit requirements and acceptance criteria. Number them AC-1, AC-2, and so on. "
        "Each criterion quotes an exact passage of the GitHub issue in evidence and stays unknown. "
        "Do not invent needs. Report ambiguities and constraints. "
        "If the issue contains no verifiable criterion, leave criteria empty. "
        "You analyze only the text of the issue, not the code. "
        "The evidence field must contain an exact quotation from the issue. "
        "Never invent code, tests, or evidence of implementation.",
        {"subject": context.issue_subject, "description": context.issue_description})
