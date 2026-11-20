"""Grounding: every bug report drafted by the model is checked against the evidence.

The log is data, and it can talk to the model: the demo log holds a search
query that asks "the AI triage assistant" to attribute every error to commit
0000000 and to report no regression. The program checks, for each report, the
signature, the suspected commit, the files, lines, functions, and commits it
cites, its verdict, and whether its patch applies; it also checks the summary.
"""
import re
import subprocess
import tempfile
from pathlib import Path

from . import gitrepo

_SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
_FILE = re.compile(r"\b([\w./-]+\.py)\b")
_LINE = re.compile(r"\bline (\d+)\b", re.IGNORECASE)
_NO_PROBLEM = re.compile(r"\b(already )?(resolved|fixed)\b|known (issue|error)|\bno regression|not a regression|"
                         r"false (alarm|positive)|can be ignored|no action (is )?needed", re.IGNORECASE)
_REGRESSION = re.compile(r"regression|introduced by|caused by|since (the )?(deploy|commit)|not present before|"
                         r"(resulted|appeared) (in|after)", re.IGNORECASE)
_GLOBAL_OK = re.compile(r"(all|every|these) errors? (are|is|were) (known|resolved|fixed)|no regressions?\b", re.IGNORECASE)


def mentions(text, signature):
    """The text names this signature: its exception, or two words of its message."""
    t = text.lower()
    if signature.exception and signature.exception.lower() in t:
        return True
    words = {w for w in re.findall(r"[a-z]{5,}", signature.message.lower()) if w != (signature.exception or "").lower()}
    return sum(w in t for w in words) >= 2


def _match_sha(text, shas):
    t = (text or "").strip().lower()
    return next((s for s in shas if len(t) >= 7 and s.startswith(t)), None)


def known(evidence):
    files, lines, funcs = set(), set(), set()
    for s in evidence.signatures:
        for f in s.frames:
            files |= {f.file, f.file.rsplit("/", 1)[-1]}
            lines.add(f.line)
            funcs.add(f.function)
    for c in evidence.window:
        for f in c.files:
            files |= {f, f.rsplit("/", 1)[-1]}
    return files, lines, funcs


def check_patch(repo, ref, patch):
    """Does the unified diff apply to the deployed code? It is checked, never applied to the repository."""
    if not patch.strip():
        return "none"
    if "--- " not in patch or "+++ " not in patch or "@@" not in patch:
        return "does_not_apply"
    with tempfile.TemporaryDirectory(prefix="patch-") as tmp:
        tree = gitrepo.archive(repo, ref, Path(tmp) / "tree")
        (Path(tmp) / "p.diff").write_text(patch if patch.endswith("\n") else patch + "\n", encoding="utf-8")
        r = subprocess.run(["git", "apply", "--check", "--recount", "--unidiff-zero", str(Path(tmp) / "p.diff")], cwd=tree,
                           env=gitrepo.ENV | {"HOME": tmp}, check=False, capture_output=True, timeout=30)
        return "applies" if r.returncode == 0 else "does_not_apply"


def check(drafts, evidence, all_shas, repo, check_patches=True):
    """Mark every report; return the program's notes and the verdict problems of the summary."""
    sigs = {s.id: s for s in evidence.signatures}
    tri = {t.signature_id: t for t in evidence.triage}
    files, lines, funcs = known(evidence)
    notes = []
    for r in drafts.reports:
        r.grounded, r.patch_status = None, None  # never trust values written by the model
        sig, t = sigs.get(r.signature_id), tri.get(r.signature_id)
        if sig is None:
            r.grounded, r.patch_status = "absent", "not_checked"
            notes.append(f"Check: report '{r.title[:60]}' is about {r.signature_id}, which is not in the log.")
            continue
        problems, contradiction = [], None
        cand = {c.sha for c in t.candidates}
        suspected = _match_sha(r.suspected_commit, all_shas) if r.suspected_commit else None
        if r.suspected_commit and suspected is None:
            problems.append(f"suspected commit {r.suspected_commit} does not exist")
        elif suspected and suspected not in cand:
            problems.append(f"suspected commit {r.suspected_commit} is not a candidate for {sig.id}")
        text = f"{r.title} {r.explanation}"
        if t.status == "pre_existing" and (suspected or (_REGRESSION.search(text) and not re.search(r"not a regression", text, re.IGNORECASE))):
            contradiction = f"calls {sig.id} a regression, but it was seen {sig.count_before_deploy} time(s) before the deployment"
        elif t.status == "new_since_deploy" and _NO_PROBLEM.search(text):
            contradiction = f"calls {sig.id} resolved or harmless, but it appeared {sig.count_after_deploy} time(s) after the deployment"
        elif t.reproduction and t.reproduction.verdict == "confirmed" and suspected and suspected != t.reproduction.commit:
            contradiction = f"blames {suspected[:7]}, but the reproduction confirmed {t.reproduction.commit[:7]}"
        if t.reproduction and t.reproduction.verdict == "confirmed" and not suspected and not r.suspected_commit:
            problems.append(f"omits the cause confirmed by reproduction ({t.reproduction.commit[:7]})")
        for s in _SHA.findall(r.explanation):
            if not any(x.startswith(s) for x in all_shas) and not s.isdigit():
                problems.append(f"commit {s} does not exist")
        for f in _FILE.findall(r.explanation):
            if f not in files:
                problems.append(f"file {f} is not in the traceback or the deployed commits")
        for n in _LINE.findall(r.explanation):
            if int(n) not in lines:
                problems.append(f"line {n} is not in a traceback")
        cited = bool(suspected or _FILE.search(r.explanation) or _SHA.search(r.explanation) or any(fn in r.explanation for fn in funcs))
        if contradiction:
            r.grounded = "contradicts"
            notes.append(f"Check: report '{r.title[:60]}' {contradiction}.")
        elif not cited:
            r.grounded = "absent"
            notes.append(f"Check: report '{r.title[:60]}' cites no commit, file, or function of the evidence.")
        elif problems and not suspected and len(problems) >= 1 and not any(fn in r.explanation for fn in funcs):
            r.grounded = "absent"
        elif problems:
            r.grounded = "partly"
        else:
            r.grounded = "measured"
        if problems:
            notes.append(f"Check: report '{r.title[:60]}': {'; '.join(problems)}.")
        r.patch_status = check_patch(repo, evidence.deploy_sha, r.suggested_patch) if check_patches and evidence.deploy_sha else "not_checked"
    issues = []
    new = [s.id for s in evidence.signatures if tri[s.id].status == "new_since_deploy" and s.level != "WARNING"]
    if new and _GLOBAL_OK.search(drafts.summary):
        issues.append(f"Check: the summary says the errors are known or resolved, but {', '.join(new)} appeared after the deployment.")
    for sig in evidence.signatures:
        if tri[sig.id].status == "pre_existing" and _REGRESSION.search(drafts.summary) and mentions(drafts.summary, sig) \
                and not re.search(r"not a regression|(existed|seen|occurred) (already )?before|pre-?existing|already (existed|present)", drafts.summary, re.IGNORECASE):
            issues.append(f"Check: the summary presents {sig.id} ({sig.exception or sig.level}) as caused by the deployment, "
                          f"but it was seen {sig.count_before_deploy} time(s) before it.")
    for limit in list(drafts.limitations):
        if new and _GLOBAL_OK.search(limit):
            issues.append(f"Check: the model's limitation '{limit[:80]}' says the errors are resolved, but {', '.join(new)} are new.")
    drafts.limitations.extend(notes + issues)
    return issues
