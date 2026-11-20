"""Contracts: every exchange is validated; the model cannot add fields."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Produced by the program, never by the model.

class FunctionMetrics(StrictModel):
    module: str
    name: str            # qualified inside the module, e.g. Loan.due_date
    line: int
    length: int
    complexity: int


class ModuleMetrics(StrictModel):
    name: str            # dotted, e.g. library.domain.loan
    path: str            # relative to the repository root
    lines: int           # non-blank, non-comment lines
    layer: str | None
    fan_in: int = 0      # afferent coupling (Ca)
    fan_out: int = 0     # efferent coupling (Ce)
    instability: float = 0.0  # Ce / (Ca + Ce)


class Dependency(StrictModel):
    source: str
    target: str
    line: int


class Violation(StrictModel):
    kind: Literal["layer", "cycle", "complexity", "long_function", "duplicate_block", "marker"]
    location: str        # module, module:function, or module:line
    detail: str
    measured: float | None = None
    threshold: float | None = None
    remediation_min: int


class Marker(StrictModel):
    id: int
    module: str
    line: int
    tag: Literal["TODO", "FIXME", "HACK", "XXX"]
    text: str


class Measurement(StrictModel):
    root: str
    files: int
    skipped: list[str]
    parse_errors: list[str]
    total_lines: int
    modules: list[ModuleMetrics]
    functions: list[FunctionMetrics]
    dependencies: list[Dependency]
    cycles: list[list[str]]
    duplicated_lines: int
    duplication_pct: float
    markers: list[Marker]
    violations: list[Violation]
    remediation_min: int
    debt_ratio_pct: float


class GateResult(StrictModel):
    id: str
    text: str
    metric: str
    status: Literal["met", "not_met", "not_measured"]
    measured: float | None = None
    threshold: float


# Produced by the model, then checked by the program.

class MarkerClass(StrictModel):
    marker_id: int
    debt_type: Literal["design", "code", "test", "documentation", "requirement", "defect", "other"]
    rationale: str = Field(default="", max_length=500)


class Classification(StrictModel):
    items: list[MarkerClass] = Field(default_factory=list, max_length=200)


class Finding(StrictModel):
    severity: Literal["info", "low", "medium", "high"]
    title: str = Field(max_length=200)
    location: str = Field(max_length=200)        # module or module:function
    evidence: str = Field(max_length=1500)       # must cite measured names and numbers
    recommendation: str = Field(max_length=1500)
    source: Literal["model", "tool"] = "model"   # set by the program
    grounded: Literal["measured", "partly", "absent", "contradicts"] | None = None  # set by the program


class Analysis(StrictModel):
    summary: str = Field(max_length=3000)
    findings: list[Finding] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=40)


class Report(StrictModel):
    run_id: str
    created_at: str
    model: str
    measurement: Measurement
    gates: list[GateResult]
    classification: Classification
    analysis: Analysis
    decision: Literal["changes_recommended", "human_review_required", "ready_for_human_approval"]
    reasons: list[str]
    human_approval_required: Literal[True] = True
