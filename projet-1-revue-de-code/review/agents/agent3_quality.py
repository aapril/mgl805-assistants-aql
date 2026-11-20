"""Agent 3: readability and Ruff results."""
from .common import analyze, code_payload, append_tools


def run(context, model):
    payload = code_payload(context)
    payload["ruff"] = context.evidence.tools["ruff"].model_dump() if context.evidence and "ruff" in context.evidence.tools else None
    result = analyze(model, 3,
        "Assess readability, visible duplication, responsibilities, and maintainability. "
        "Explain the concrete impact of each deviation. The Ruff report may be missing. "
        "Do not copy Ruff findings into findings: the program will add them. "
        "A Ruff report with status=passed and no finding means that Ruff detected no deviation, not that the report is missing.",
        payload)
    return append_tools(result, context, ["ruff"])
