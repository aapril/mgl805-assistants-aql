"""GitHub API connectors: PR diff, linked issue, and review comments."""
import re

from .http import Client
from .models import Context

COMMENT_MARKER = "<!-- ai-review-bot -->"
ISSUE_REFERENCE = re.compile(
    r"\b(?:closes?|closed|fix(?:es|ed)?|resolves?|resolved|issue|ticket)\s*:?\s*#([1-9]\d*)\b",
    re.IGNORECASE,
)


def repo_path(repository: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or any(
        x in (".", "..") for x in repository.split("/")
    ):
        raise ValueError("The repository must have the form owner/repo")
    return "/repos/" + repository


def linked_issue(body: str | None) -> int | None:
    """Read the first explicitly linked issue (e.g. 'Closes #12')."""
    match = ISSUE_REFERENCE.search(body or "")
    return int(match.group(1)) if match else None


class GitHub:
    def __init__(self, url, token, api_version="2026-03-10"):
        self.http = Client(url, {
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": api_version,
            "User-Agent": "ai-review-github/0.4.0",
        })

    def pull(self, repository, pr):
        return self.http.request("GET", f"{repo_path(repository)}/pulls/{int(pr)}")

    def issue(self, repository, issue_number):
        return self.http.request("GET", f"{repo_path(repository)}/issues/{int(issue_number)}")

    def diff(self, repository, pr):
        return self.http.request(
            "GET", f"{repo_path(repository)}/pulls/{int(pr)}",
            as_text=True, accept="application/vnd.github.diff"
        )

    def comment(self, repository, pr, text):
        return self.http.request("POST", f"{repo_path(repository)}/issues/{int(pr)}/comments", {"body": text})

    def review_comment(self, repository, pr, text):
        """Keep a single bot-owned summary comment across Action reruns."""
        base = f"{repo_path(repository)}/issues/{int(pr)}/comments"
        for page in range(1, 6):
            comments = self.http.request("GET", f"{base}?per_page=100&page={page}")
            for comment in comments:
                user = comment.get("user") or {}
                if (
                    user.get("login") == "github-actions[bot]"
                    and COMMENT_MARKER in (comment.get("body") or "")
                ):
                    return self.http.request(
                        "PATCH",
                        f"{repo_path(repository)}/issues/comments/{int(comment['id'])}",
                        {"body": text},
                    )
            if len(comments) < 100:
                break
        return self.comment(repository, pr, text)


def fetch_context(git, repository, pr, issue_id=None, standards="", evidence=None):
    before = git.pull(repository, pr)
    if before.get("state") != "open" or before.get("merged"):
        raise ValueError("The pull request must be open")
    issue_id = issue_id or linked_issue(before.get("body"))
    if not issue_id:
        raise ValueError("GitHub issue not found. Add 'Closes #12' to the PR or use --issue 12.")
    ticket = git.issue(repository, issue_id)
    if "pull_request" in ticket:
        raise ValueError("The number given is a PR, not a GitHub issue")
    diff = git.diff(repository, pr)
    after = git.pull(repository, pr)
    for branch in ("head", "base"):
        if before[branch]["sha"] != after[branch]["sha"]:
            raise ValueError("The code changed while it was being read. Run the review again.")
    if len(diff) > 45_000:
        raise ValueError("Diff longer than 45,000 characters; split the PR. No silent truncation.")
    description = ticket.get("body") or ""
    if len(description) > 15_000:
        raise ValueError("Issue description too long; maximum 15,000 characters")
    if len(standards) > 10_000:
        raise ValueError("Standards too long; maximum 10,000 characters")
    return Context(
        issue_id=issue_id, issue_subject=ticket["title"], issue_description=description,
        issue_updated_at=ticket["updated_at"], repository=repository, pr=pr,
        head_sha=before["head"]["sha"], base_sha=before["base"]["sha"],
        pr_title=before["title"], diff=diff, standards=standards, evidence=evidence,
        warnings=["Diff-only analysis: unchanged files, binaries, and repository context were not inspected."],
    )
