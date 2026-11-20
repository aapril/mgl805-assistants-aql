"""Git, read only: references, commits, diffs, blame, and archives of a commit.

Every command reads the repository; none changes it. A commit is checked out
only as an archive in a temporary folder, for a reproduction or a patch check.
"""
import io
import os
import subprocess
import tarfile
from pathlib import Path

ENV = {"PATH": os.environ.get("PATH", ""), "GIT_CONFIG_NOSYSTEM": "1", "GIT_PAGER": "cat", "LC_ALL": "C"}


class GitError(RuntimeError):
    pass


def git(repo, *args, binary=False):
    r = subprocess.run(["git", "-C", str(repo), "--no-pager", *args], env=ENV | {"HOME": str(repo)},
                       check=False, capture_output=True, timeout=60)
    if r.returncode:
        raise GitError(f"git {' '.join(args[:3])}: {r.stderr.decode(errors='replace').strip()[:200]}")
    return r.stdout if binary else r.stdout.decode("utf-8", errors="replace")


def is_repo(repo):
    try:
        return git(repo, "rev-parse", "--is-inside-work-tree").strip() == "true"
    except (GitError, FileNotFoundError, NotADirectoryError):
        return False


def resolve(repo, ref):
    try:
        return git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").strip() or None
    except GitError:
        return None


def window(repo, previous, current):
    """Commits reachable from current but not from previous, oldest first."""
    spec = f"{previous}..{current}" if previous else current
    return git(repo, "rev-list", "--reverse", spec).split()


def commit(repo, sha, max_diff):
    head = git(repo, "show", "-s", "--format=%H%n%h%n%cI%n%s", sha).splitlines()
    files = [f for f in git(repo, "show", "--format=", "--name-only", sha).splitlines() if f]
    diff = git(repo, "show", "--format=", "--unified=0", "--no-color", sha)
    return {"sha": head[0], "short": head[1], "date": head[2], "subject": head[3], "files": files,
            "diff": diff[:max_diff]}


def blame(repo, ref, file, line):
    """The commit that last changed this line, as of ref, or None."""
    try:
        out = git(repo, "blame", "--porcelain", "-L", f"{line},{line}", ref, "--", file)
    except GitError:
        return None
    return out.split(" ", 1)[0] if out else None


def parent(repo, sha):
    return resolve(repo, f"{sha}^")


def file_at(repo, ref, file):
    try:
        return git(repo, "show", f"{ref}:{file}")
    except GitError:
        return None


def archive(repo, sha, dest):
    """Extract the tree of a commit into dest, without links or absolute paths."""
    data = git(repo, "archive", "--format=tar", sha, binary=True)
    dest = Path(dest)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        try:
            tar.extractall(dest, filter="data")
        except TypeError:  # Python 3.11 before 3.11.4: check every member by hand
            for m in tar.getmembers():
                if not (m.isfile() or m.isdir()) or m.name.startswith("/") or ".." in Path(m.name).parts:
                    raise GitError(f"Unsafe archive member: {m.name}") from None
            tar.extractall(dest)  # members checked above
    return dest
