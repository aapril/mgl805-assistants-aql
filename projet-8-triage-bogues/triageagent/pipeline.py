"""Fixed order: read the log, find the deployment, group, correlate, reproduce, draft, ground, decide."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import correlate, gitrepo, grounding, logs, repro
from .contracts import Commit, Drafts, Evidence, Report
from .decision import decide


class UnsafeInput(ValueError):
    pass


def excerpt(repo, ref, frame, context):
    text = gitrepo.file_at(repo, ref, frame.file)
    if text is None:
        return None
    lines = text.splitlines()
    lo, hi = max(1, frame.line - context), min(len(lines), frame.line + context)
    return {"file": frame.file, "line": frame.line,
            "code": "\n".join(f"{i:4}{'>' if i == frame.line else ' '} {lines[i - 1]}" for i in range(lo, hi + 1))}


def gather(log_path, repo, config, allow_execution=False):
    limits = config["limits"]
    log_path = Path(log_path)
    if log_path.stat().st_size > limits["max_log_bytes"]:
        raise UnsafeInput(f"Log larger than max_log_bytes ({limits['max_log_bytes']}); cut it to the period to triage.")
    if not gitrepo.is_repo(repo):
        raise UnsafeInput(f"'{repo}' is not a Git repository.")
    recs = logs.records(log_path.read_text(encoding="utf-8", errors="replace"))
    deploys = logs.deployments(recs, config["deploy_pattern"])
    deploy_time, ref = deploys[-1] if deploys else (None, None)
    previous = deploys[-2][1] if len(deploys) > 1 else None
    sha = gitrepo.resolve(repo, ref) if ref else None
    prev_sha = gitrepo.resolve(repo, previous) if previous else None
    commits = [Commit(**gitrepo.commit(repo, s, limits["max_diff_chars"])) for s in gitrepo.window(repo, prev_sha, sha)] if sha else []
    has_history = bool(deploy_time) and any(r["time"] < deploy_time for r in recs)
    sigs = logs.signatures(recs, config["path_prefixes"], deploy_time, limits["max_signatures"])
    execution = config.get("execution", {})
    if not execution.get("allowed"):
        mode = "not allowed by the configuration"
    elif not allow_execution:
        mode = "not requested: add --allow-execution to run the reproductions"
    else:
        mode = "allowed"
    triage = []
    for s in sigs:
        t = correlate.triage(repo, s, commits, sha, deploy_time, has_history)
        if mode == "allowed" and t.status == "new_since_deploy":
            for c in t.candidates[:3]:  # bounded: at most three candidates, two runs each
                r = repro.reproduce(repo, s, c.sha, execution)
                if r is None:
                    break
                t.reproduction = r
                if r.verdict == "confirmed":
                    t.attribution = "confirmed"
                    t.candidates = [c] + [x for x in t.candidates if x.sha != c.sha]
                    break
        triage.append(t)
    return Evidence(log=log_path.name, repo=Path(repo).name, deploy_ref=ref, deploy_sha=sha, previous_ref=previous,
                    deploy_time=deploy_time, window=commits, signatures=sigs, triage=triage, execution=mode)


def run(log_path, repo, config, model, allow_execution=False, check_patches=True):
    ev = gather(log_path, repo, config, allow_execution)
    ctx = config["limits"]["excerpt_context"]
    payload = {"deployment": {"ref": ev.deploy_ref, "commit": ev.deploy_sha, "previous": ev.previous_ref, "time": ev.deploy_time},
               "deployed_commits": [c.model_dump() for c in ev.window],
               "signatures": [s.model_dump(exclude={"suspicious"}) for s in ev.signatures],
               "triage": [t.model_dump() for t in ev.triage],
               "code": [x for s in ev.signatures for f in s.frames if (x := excerpt(repo, ev.deploy_sha, f, ctx))] if ev.deploy_sha else []}
    try:
        drafts = model.draft(payload)
    except Exception as exc:  # noqa: BLE001 - a failed draft never hides the evidence
        drafts = Drafts(summary="Drafts not completed.", limitations=[f"Check: failure {type(exc).__name__}: {str(exc)[:200]}"])
    all_shas = gitrepo.git(repo, "rev-list", "--all").split()
    issues = grounding.check(drafts, ev, all_shas, repo, check_patches)
    decision, reasons = decide(ev, drafts, issues)
    return Report(run_id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(), model=model.name,
                  evidence=ev, drafts=drafts, decision=decision, reasons=reasons)
