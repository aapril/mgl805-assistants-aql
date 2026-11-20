"""Agent 2: technical risks in the changed lines."""
from .common import analyze, code_payload


def run(context, model):
    return analyze(model, 2,
        "Analyze the diff: logic errors, boundary cases, compatibility, and visible dependencies. "
        "Separate facts from hypotheses. Cite the file, the new line number if known, and an excerpt of the diff. "
        "Do not invent the content of other files. Do not compute a numeric complexity without a tool. "
        "Compare the function names, signatures, and behaviors in the diff with the requirements of the issue. "
        "Report concrete deviations. "
        "Do not treat files you have not inspected as defects.",
        code_payload(context))
