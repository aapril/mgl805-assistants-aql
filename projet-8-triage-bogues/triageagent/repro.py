"""Reproduction: run a test written by a person at the suspected commit and at its parent.

This is the only step that runs code of the analyzed repository, so it needs
two permissions: execution.allowed in the configuration, and --allow-execution
on the command line. The command comes from the configuration, never from the
model. Each commit is extracted into a temporary folder; the repository
itself is never modified. A failure at the commit and a pass at its parent
confirm the cause, like one step of git bisect.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from . import gitrepo
from .contracts import Reproduction


def _run(repo, sha, command, repro_dir, timeout):
    with tempfile.TemporaryDirectory(prefix="triage-") as tmp:
        tree = gitrepo.archive(repo, sha, Path(tmp) / "tree")
        cmd = [sys.executable if c == "python" else c for c in command]
        env = {"PATH": os.environ.get("PATH", ""), "HOME": tmp, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
               "PYTHONPATH": os.pathsep.join([str(tree), str(Path(repro_dir).resolve())])}
        try:
            r = subprocess.run(cmd, cwd=tree, env=env, check=False, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "timeout"
        except OSError:
            return "error"
        return "pass" if r.returncode == 0 else "fail"


def reproduce(repo, signature, sha, execution):
    rule = next((r for r in execution.get("reproductions", []) if r["exception"] == signature.exception), None)
    parent = gitrepo.parent(repo, sha)
    if rule is None or parent is None:
        return None
    at_commit = _run(repo, sha, rule["command"], execution["repro_dir"], execution["timeout_s"])
    at_parent = _run(repo, parent, rule["command"], execution["repro_dir"], execution["timeout_s"])
    verdict = "confirmed" if at_commit == "fail" and at_parent == "pass" else "not_confirmed"
    return Reproduction(command=rule["command"], commit=sha, parent=parent, at_commit=at_commit,
                        at_parent=at_parent, verdict=verdict)
