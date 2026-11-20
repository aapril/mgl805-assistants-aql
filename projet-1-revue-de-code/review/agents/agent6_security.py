"""Agent 6: security analysis, Bandit and Gitleaks."""
from .common import analyze, code_payload, append_tools


def run(context, model):
    payload = code_payload(context)
    payload["security_tools"] = {name: context.evidence.tools[name].model_dump() for name in ("bandit", "gitleaks") if context.evidence and name in context.evidence.tools}
    result = analyze(model, 6,
        "Look for injections, missing access control, input validation, and exposed secrets. "
        "Give only the locations of secrets, never their values. "
        "Report the limits of the diff. Do not copy Bandit or Gitleaks findings into findings; they will be added. "
        "The absence of findings does not prove that the application is secure.", payload)
    return append_tools(result, context, ["bandit", "gitleaks"])
