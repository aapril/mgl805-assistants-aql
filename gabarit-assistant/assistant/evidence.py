"""Deterministic evidence: tools decide what they can (book Section 5.2.2).

The tools listed in assistant_config.json run on the exact artifact, and the
result is bound to its digest. WARNING: running the tests of an artifact runs
its code. In a real pipeline, run this step in an isolated container without
secrets or network, and remember that the artifact can still forge its own
results (book Sections 5.3.1.4 and 5.4.2).
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from .artifact import digest, load
from .contracts import Evidence, ToolResult


def run_tool(name, command, timeout=300):
    command = [sys.executable if part == "{python}" else part for part in command]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ToolResult(name=name, status="error", output=str(exc)[:4000])
    output = (done.stdout + done.stderr)[-4000:]
    return ToolResult(name=name, status="passed" if done.returncode == 0 else "failed", output=output)


def collect(config_path, artifact_paths):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    tools = [run_tool(t["name"], t["command"]) for t in config["tools"]]
    return Evidence(artifact_digest=digest(load(artifact_paths)),
                    generated_at=datetime.now(timezone.utc).isoformat(), tools=tools)
