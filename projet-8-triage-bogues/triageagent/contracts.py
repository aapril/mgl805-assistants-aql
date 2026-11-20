"""Contracts: every exchange is validated; the model cannot add fields."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Produced by the program, never by the model.

class Frame(StrictModel):
    file: str            # relative to the repository root
    line: int
    function: str
    code: str = ""


class Signature(StrictModel):
    """One kind of problem in the log: same level, exception, message, and place."""
    id: str
    level: Literal["ERROR", "CRITICAL", "WARNING"]
    exception: str | None
    message: str
    frames: list[Frame]
    count: int
    count_before_deploy: int
    count_after_deploy: int
    first_seen: str
    last_seen: str
    sample: str
    suspicious: list[str] = Field(default_factory=list)   # text addressed to an AI, found in the log


class Commit(StrictModel):
    sha: str
    short: str
    date: str
    subject: str
    files: list[str]
    diff: str            # truncated


class Candidate(StrictModel):
    sha: str
    short: str
    subject: str
    score: int
    evidence: list[str]


class Reproduction(StrictModel):
    command: list[str]
    commit: str
    parent: str
    at_commit: Literal["fail", "pass", "timeout", "error"]
    at_parent: Literal["fail", "pass", "timeout", "error"]
    verdict: Literal["confirmed", "not_confirmed"]


class Triage(StrictModel):
    signature_id: str
    status: Literal["new_since_deploy", "pre_existing", "unknown"]
    candidates: list[Candidate]
    notes: list[str]
    reproduction: Reproduction | None = None
    attribution: Literal["confirmed", "probable", "uncertain", "pre_existing"]


class Evidence(StrictModel):
    log: str
    repo: str
    deploy_ref: str | None
    deploy_sha: str | None
    previous_ref: str | None
    deploy_time: str | None
    window: list[Commit]          # commits deployed by the last deployment
    signatures: list[Signature]
    triage: list[Triage]
    execution: str                # what was allowed to run


# Produced by the model, then checked by the program.

class BugReport(StrictModel):
    signature_id: str = Field(max_length=20)
    title: str = Field(max_length=200)
    severity: Literal["low", "medium", "high", "critical"]
    suspected_commit: str | None = Field(default=None, max_length=40)
    explanation: str = Field(max_length=2000)        # must cite files, lines, commits from the evidence
    suggested_patch: str = Field(default="", max_length=4000)   # a unified diff, never applied
    next_steps: str = Field(default="", max_length=1000)
    grounded: Literal["measured", "partly", "absent", "contradicts"] | None = None   # set by the program
    patch_status: Literal["applies", "does_not_apply", "none", "not_checked"] | None = None  # set by the program


class Drafts(StrictModel):
    summary: str = Field(max_length=3000)
    reports: list[BugReport] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=40)


class Report(StrictModel):
    run_id: str
    created_at: str
    model: str
    evidence: Evidence
    drafts: Drafts
    decision: Literal["regressions_found", "human_review_required", "no_new_errors"]
    reasons: list[str]
    human_approval_required: Literal[True] = True
