"""Grounding: is the evidence really in the artifact? (book Section 5.3.1.5)

The contracts check the structure of the evidence, not its truth. This module
checks every quotation that can be checked mechanically, and says WHERE it was
found: a name that only the reference contains proves nothing about the artifact.

- findings: "artifact", "reference_only", "absent", or None (prose only);
- criteria of the agent "criteria": the evidence must copy the reference exactly;
- criteria of other agents: a verdict (supported or not_met) must quote the
  artifact; otherwise the criterion goes back to unknown.
"""
import re

_DIFF_LINE = re.compile(r"^(diff --git |index |--- |\+\+\+ |@@ |[+\- ])")


def flat(text: str) -> str:
    return " ".join(text.split())


def quotations(evidence: str) -> list[str]:
    quotes = [q for q in re.findall(r"`([^`\n]+)`", evidence) if len(q.strip()) > 2]
    lines = evidence.splitlines()
    if len(lines) > 1 and sum(bool(_DIFF_LINE.match(x)) for x in lines) >= 2:
        for line in lines:
            if line[:1] in "+- " and not line.startswith(("+++", "---")):
                line = line[1:]
            if len(line.strip()) > 2:
                quotes.append(line)
    return quotes


def locate(evidence: str, artifact: str, reference: str):
    """Return (absent, reference_only) quotations of the evidence."""
    in_artifact, in_reference = flat(artifact), flat(reference)
    absent, reference_only = [], []
    for q in quotations(evidence):
        f = flat(q)
        if f in in_artifact:
            continue
        (reference_only if f in in_reference else absent).append(q.strip())
    return absent, reference_only


def check(results, artifact: str, reference: str):
    for result in results:
        for f in result.findings:
            if f.source != "model":
                continue
            f.grounded = None  # never trust a value written by the model
            absent, ref_only = locate(f.evidence, artifact, reference)
            if absent:
                f.grounded = "absent"
                result.limitations.append(f"Finding '{f.title[:80]}': quotation not found: {absent[0][:120]!r}.")
            elif ref_only:
                f.grounded = "reference_only"
                result.limitations.append(f"Finding '{f.title[:80]}' cites {ref_only[0][:60]!r}, found in the reference but not in the artifact.")
            elif quotations(f.evidence):
                f.grounded = "artifact"
        for c in result.criteria:
            if result.agent == "criteria":
                if flat(c.evidence) not in flat(reference):
                    result.limitations.append(f"Criterion {c.id}: its evidence does not copy the reference.")
                    c.evidence = ""
                c.status = "unknown"
            elif c.status != "unknown":
                absent, ref_only = locate(c.evidence, artifact, reference)
                if absent or ref_only or not quotations(c.evidence):
                    result.limitations.append(f"Criterion {c.id}: verdict {c.status} without a quotation of the artifact; set to unknown.")
                    c.status = "unknown"
    return results
