"""Contracts: every exchange is validated (book Section 5.3.1.3).

Keep these classes when you adapt the template. Change the enumerations
(severities, statuses) only together with the decision rule and its tests.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")  # the model cannot add fields


class Finding(StrictModel):
    severity: Literal["info", "low", "medium", "high"]
    title: str = Field(max_length=200)
    evidence: str = Field(max_length=1500)  # quote the artifact between backticks
    recommendation: str = Field(max_length=1500)
    location: str | None = Field(default=None, max_length=300)
    source: Literal["model", "tool"] = "model"  # set by the program
    grounded: Literal["artifact", "reference_only",
                      "absent"] | None = None  # set by the program


class Criterion(StrictModel):
    id: str = Field(max_length=40)
    text: str = Field(max_length=1000)
    status: Literal["supported", "not_met", "unknown"] = "unknown"
    evidence: str = Field(default="", max_length=1500)


class AgentResult(StrictModel):
    agent: str = Field(max_length=40)
    status: Literal["complete", "incomplete"]
    summary: str = Field(max_length=3000)
    findings: list[Finding] = Field(default_factory=list, max_length=40)
    criteria: list[Criterion] = Field(default_factory=list, max_length=40)
    limitations: list[str] = Field(default_factory=list, max_length=30)


class ToolResult(StrictModel):
    name: str
    status: Literal["passed", "failed", "error"]
    output: str = Field(default="", max_length=4000)


class Evidence(StrictModel):
    artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    generated_at: str
    tools: list[ToolResult]


class Report(StrictModel):
    run_id: str
    created_at: str
    assistant: str
    model: str
    artifact_digest: str
    input_digest: str
    results: list[AgentResult]
    tools: list[ToolResult]
    decision: Literal["changes_recommended", "human_review_required",
                      "ready_for_human_approval"]
    reasons: list[str]
    human_approval_required: Literal[True] = True
