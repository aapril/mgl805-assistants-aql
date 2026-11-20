"""Publish a GitHub-only PR summary; check commit/issue freshness first."""
import json
from pathlib import Path
from .report import publication_text


def publish(review, git, journal: Path):
    if review.demo:
        raise ValueError("Publishing a simulation is forbidden")
    state = json.loads(journal.read_text()) if journal.exists() else {}
    if state.get("run_id", review.run_id) != review.run_id:
        raise ValueError("Publication journal belongs to another review")
    if state.get("github") == "sent":
        return state
    pull = git.pull(review.repository, review.pr)
    if (
        pull.get("state") != "open" or pull.get("merged")
        or pull["head"]["sha"] != review.head_sha
        or pull["base"]["sha"] != review.base_sha
    ):
        raise ValueError("PR closed or commits changed since the review. Run the analysis again.")
    if git.issue(review.repository, review.issue_id)["updated_at"] != review.issue_updated_at:
        raise ValueError("GitHub issue changed since the review. Run the analysis again.")
    if state.get("github") == "sending":
        raise ValueError("GitHub sending uncertain. Check the PR and the journal before trying again.")
    state.update(run_id=review.run_id, github="sending")
    journal.write_text(json.dumps(state, indent=2), encoding="utf-8")
    # The bot updates its previous review comment instead of adding one per PR push.
    git.review_comment(review.repository, review.pr, publication_text(review))
    state["github"] = "sent"
    journal.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state
