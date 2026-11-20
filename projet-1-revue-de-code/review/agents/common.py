from ..models import AgentResult


def analyze(model, number, instruction, payload):
    try:
        return model.analyze(number, instruction, payload)
    except Exception as exc:
        # A failure stays visible; there is no favorable result by default.
        return AgentResult(agent=number, status="incomplete", summary="Analysis not completed.",
            limitations=[f"Failure {type(exc).__name__}; check the service and run again."])



def code_payload(context):
    return {
        "issue": {
            "title": context.issue_subject,
            "description": context.issue_description,
        },
        "diff": context.diff,
        "standards": context.standards,
        "head_sha": context.head_sha,
    }



def append_tools(result, context, names):
    for name in names:
        tool = context.evidence.tools.get(name) if context.evidence else None
        if not tool or tool.status in ("not_run", "error"):
            result.limitations.append(f"{name} not run or in error.")
        if tool:
            # Deterministic findings do not depend on how faithfully the model summarizes them.
            result.findings.extend(tool.findings[:40])
            if tool.total_findings > 40:
                result.limitations.append(f"{name}: only 40 of {tool.total_findings} findings shown.")
    return result
