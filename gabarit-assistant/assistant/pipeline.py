"""The orchestration: fixed order, validated inputs and outputs (book Figure 5.1)."""
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4
from .agents import AGENTS
from .artifact import as_text, digest
from .contracts import AgentResult, Report
from .decision import decide
from . import grounding


def run(assistant_name, reference_text, artifact_files, evidence, model):
    artifact = as_text(artifact_files)
    current = digest(artifact_files)
    inputs = {"reference": reference_text, "artifact": artifact,
              "tools": [t.model_dump() for t in evidence.tools] if evidence else []}
    results = []
    for agent in AGENTS:
        payload = {name: inputs[name] for name in agent.inputs if name in inputs}
        if "criteria" in agent.inputs:
            payload["criteria"] = [c.model_dump() for r in results for c in r.criteria]
        try:
            result = model.analyze(agent, payload)
        except Exception as exc:  # a failure stays visible; never a favorable default
            result = AgentResult(agent=agent.name, status="incomplete", summary="Analysis not completed.",
                                 limitations=[f"Failure {type(exc).__name__}: {str(exc)[:200]}"])
        for f in result.findings:
            f.source = "model"
        results.append(result)
        if agent.name == "criteria":
            grounding.check([result], artifact, reference_text)
            inputs["criteria"] = [c.model_dump() for c in result.criteria]
    grounding.check([r for r in results if r.agent != "criteria"], artifact, reference_text)
    decision, reasons = decide(results, evidence, current)
    input_digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    return Report(run_id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(),
                  assistant=assistant_name, model=model.name, artifact_digest=current,
                  input_digest=input_digest, results=results,
                  tools=evidence.tools if evidence else [], decision=decision, reasons=reasons)
