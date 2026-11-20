"""Correlation: which deployed commits could have caused each new signature.

For each signature that appeared after the last deployment, every commit of
that deployment receives points for three kinds of evidence:

- blame (3 points): the commit last changed a line of the traceback;
- file (2 points): the commit changed a file that appears in the traceback;
- token (2 points): the commit's diff contains a name from the error message,
  such as the key of a KeyError.

Blame alone misleads when the failing line is old and the cause is elsewhere:
the program notes it. The score orders the candidates; it does not decide.
"""
import re

from . import gitrepo
from .contracts import Candidate, Triage

_TOKEN = re.compile(r"'([A-Za-z_]\w{2,})'|\"([A-Za-z_]\w{2,})\"|\b([a-z_]+_[a-z_]+)\b")


def tokens(message):
    return {next(t for t in m if t) for m in _TOKEN.findall(message or "")}


def triage(repo, signature, commits, deploy_sha, deploy_time, has_history):
    notes = []
    if signature.count_before_deploy:
        return Triage(signature_id=signature.id, status="pre_existing", candidates=[], attribution="pre_existing",
                      notes=[f"Seen {signature.count_before_deploy} time(s) before the deployment: not caused by it."])
    if not deploy_sha or not has_history:
        return Triage(signature_id=signature.id, status="unknown", candidates=[], attribution="uncertain",
                      notes=["No deployment or no log before it: cannot tell whether the problem is new."])
    by_sha = {c.sha: c for c in commits}
    scores = {c.sha: (0, []) for c in commits}
    in_repo = [f for f in signature.frames if not f.file.startswith("/")]
    for f in in_repo:
        who = gitrepo.blame(repo, deploy_sha, f.file, f.line)
        if who in by_sha:
            s, ev = scores[who]
            scores[who] = (s + 3, ev + [f"last changed {f.file} line {f.line} ({f.function}), a line of the traceback"])
        elif who:
            short = who[:7]
            notes.append(f"{f.file} line {f.line} was last changed by {short}, before the previous deployment: "
                         "blame alone would point at an old commit.")
    files = {f.file for f in in_repo}
    words = tokens(signature.message)
    for c in commits:
        s, ev = scores[c.sha]
        touched = sorted(files & set(c.files))
        if touched:
            s, ev = s + 2, ev + [f"changed {', '.join(touched)}, in the traceback"]
        changed = "\n".join(l for l in c.diff.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---")))
        found = sorted(w for w in words if re.search(rf"\b{re.escape(w)}\b", changed))
        if found:
            s, ev = s + 2, ev + [f"its diff adds or removes {', '.join(repr(w) for w in found)}, named in the error"]
        scores[c.sha] = (s, ev)
    cands = sorted((Candidate(sha=sha, short=by_sha[sha].short, subject=by_sha[sha].subject, score=s, evidence=ev)
                    for sha, (s, ev) in scores.items() if s), key=lambda c: (-c.score, c.sha))
    top = cands[:1]
    unique = len(cands) == 1 or (len(cands) > 1 and cands[0].score > cands[1].score)
    attribution = "probable" if top and top[0].score >= 3 and unique else "uncertain"
    if not cands:
        notes.append("No deployed commit is linked to this signature by the evidence.")
    return Triage(signature_id=signature.id, status="new_since_deploy", candidates=cands, notes=notes, attribution=attribution)
