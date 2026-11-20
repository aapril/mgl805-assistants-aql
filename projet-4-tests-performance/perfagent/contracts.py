"""Contracts: every exchange is validated; the model cannot add fields."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Step(StrictModel):
    method: Literal["GET", "POST"] = "GET"
    path: str = Field(max_length=200)
    weight: float = Field(gt=0, le=100)
    body: dict | None = None


class Scenario(StrictModel):
    """Proposed by the planner agent, then clamped by the safety module."""
    name: str = Field(max_length=120)
    rationale: str = Field(default="", max_length=1500)
    virtual_users: int = Field(ge=1, le=1000)
    duration_s: int = Field(ge=1, le=3600)
    think_time_ms: int = Field(default=0, ge=0, le=60000)
    steps: list[Step] = Field(min_length=1, max_length=20)


class EndpointStats(StrictModel):
    method: str
    path: str
    requests: int
    errors: int
    error_rate: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float


class Measurement(StrictModel):
    """Produced by the load generator, never by the model."""
    target: str
    scenario: Scenario
    started_at: str
    elapsed_s: float
    total_requests: int
    throughput_rps: float
    error_rate: float
    endpoints: list[EndpointStats]


class SloResult(StrictModel):
    id: str
    text: str
    status: Literal["met", "not_met", "not_measured"]
    measured: float | None = None
    threshold: float


class Finding(StrictModel):
    severity: Literal["info", "low", "medium", "high"]
    title: str = Field(max_length=200)
    evidence: str = Field(max_length=1500)  # must cite measured numbers
    recommendation: str = Field(max_length=1500)
    source: Literal["model", "tool"] = "model"  # set by the program
    grounded: Literal["measured", "partly", "absent"] | None = None  # set by the program


class Analysis(StrictModel):
    summary: str = Field(max_length=3000)
    findings: list[Finding] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class Report(StrictModel):
    run_id: str
    created_at: str
    model: str
    proposed: Scenario
    executed: Scenario
    adjustments: list[str]
    measurement: Measurement | None
    slos: list[SloResult]
    analysis: Analysis
    decision: Literal["changes_recommended", "human_review_required", "ready_for_human_approval"]
    reasons: list[str]
    human_approval_required: Literal[True] = True
