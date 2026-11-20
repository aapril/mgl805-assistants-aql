"""Command line: build the demonstration repository, or triage a log."""
import argparse
import json
import sys
from pathlib import Path

from .llm import DemoModel, Ollama
from .pipeline import run
from .report import save


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m triageagent.cli")
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("demo-build", help="create the demonstration Git repository")
    b.add_argument("--target", default="demo_work")
    r = sub.add_parser("run", help="group, correlate, reproduce, draft, decide")
    r.add_argument("--repo", default="demo_work")
    r.add_argument("--log", default="examples/staging.log")
    r.add_argument("--config", default="triage_config.json")
    r.add_argument("--model", default="demo", help="demo, or an Ollama model such as qwen2.5-coder:1.5b")
    r.add_argument("--allow-execution", action="store_true",
                   help="run the reproductions of the configuration (runs code of the repository)")
    a = p.parse_args(argv)
    if a.command == "demo-build":
        from demo.history import build
        print(f"Demonstration repository created: {build(a.target)}")
        return 0
    config = json.loads(Path(a.config).read_text(encoding="utf-8"))
    model = DemoModel() if a.model == "demo" else Ollama(a.model)
    report = run(a.log, a.repo, config, model, allow_execution=a.allow_execution)
    folder = save(report)
    print(f"Report saved: {folder}")
    print(f"Recommendation: {report.decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
