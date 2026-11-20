"""Deterministic grounding: quoted evidence must exist in the reviewed artifacts.

The contracts in models.py check the structure of the evidence, not its truth.
A model can return well-formed evidence that never appeared in the diff, for
example a code excerpt in which it silently corrected the defect it reports.
This module checks every quotation that can be checked mechanically:

- lines of a diff excerpt (with or without +, - markers);
- code spans written between backticks;
- the file named by a finding, which must be a file of the diff;
- the evidence of an acceptance criterion, which must quote the issue.

It also says WHERE a quotation was found. A name taken from the requirement
proves nothing about the code: "the diff adds `subtract`" is grounded in the
issue, not in a diff that adds `substract`. Each model finding therefore gets:

- "diff": every quotation occurs in the diff;
- "issue_only": a quotation occurs in the issue or the standards, not in the diff;
- "absent": a quotation occurs nowhere, or the file is not in the diff;
- None: the evidence is prose with no checkable quotation; a person must judge it.
"""
import re

_DIFF_LINE = re.compile(r"^(diff --git |index |--- |\+\+\+ |@@ |[+\- ])")
_FILE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


def _flat(text: str) -> str:
    return " ".join(text.split())


def _quotations(evidence: str) -> list[str]:
    quotes = [q for q in re.findall(r"`([^`\n]+)`", evidence) if len(q.strip()) > 2]
    lines = evidence.splitlines()
    if len(lines) > 1 and sum(bool(_DIFF_LINE.match(x)) for x in lines) >= 2:
        for line in lines:
            if _DIFF_LINE.match(line) and line[:1] in "+- " and not line.startswith(("+++", "---")):
                line = line[1:]
            if len(line.strip()) > 2:
                quotes.append(line)
    return quotes


def missing(evidence: str, corpus: str) -> list[str]:
    """Quotations from evidence that do not occur verbatim (spacing aside) in corpus."""
    flat = _flat(corpus)
    return [q.strip() for q in _quotations(evidence) if _flat(q) not in flat]


def locate(evidence: str, diff: str, reference: str) -> tuple[list[str], list[str]]:
    """Return (absent, reference_only): quotations found nowhere, and found only outside the diff."""
    in_diff, in_ref = _flat(diff), _flat(reference)
    absent, ref_only = [], []
    for q in _quotations(evidence):
        f = _flat(q)
        if f in in_diff:
            continue
        (ref_only if f in in_ref else absent).append(q.strip())
    return absent, ref_only


def check(results, context):
    """Mark where each model finding is grounded; record why in the limitations."""
    reference = "\n".join([context.issue_subject, context.issue_description, context.standards])
    corpus = reference + "\n" + context.diff
    files = set(_FILE.findall(context.diff))
    for result in results:
        for f in result.findings:
            if f.source != "llm":
                continue
            f.grounded = None  # a value written by the model is never trusted
            absent, ref_only = locate(f.evidence, context.diff, reference)
            wrong_file = bool(f.file) and files and f.file not in files
            title = f.title[:80]
            if absent or wrong_file:
                f.grounded = "absent"
                detail = f"excerpt not in the artifacts: {absent[0][:120]!r}" if absent else f"file {f.file} not in the diff"
                result.limitations.append(f"Ungrounded evidence for finding '{title}': {detail}.")
            elif ref_only:
                f.grounded = "issue_only"
                names = ", ".join(repr(q[:60]) for q in dict.fromkeys(ref_only))
                result.limitations.append(f"Finding '{title}' cites {names}, found in the issue but not in the diff.")
            elif _quotations(f.evidence) or f.file:
                f.grounded = "diff"
        issue = context.issue_subject + "\n" + context.issue_description
        for c in result.criteria:
            # Agent 1 must quote the issue exactly; later agents may cite the code.
            absent = (_flat(c.evidence) not in _flat(issue)) if result.agent == 1 else bool(missing(c.evidence, corpus))
            if c.evidence and absent:
                c.status = "unknown"
                result.limitations.append(f"Criterion {c.id}: its evidence is not found in the artifacts.")
    return results
