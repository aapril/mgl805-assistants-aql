"""Command line: evaluate the architecture and technical debt of a Python repository."""
import argparse
import json
import sys
from pathlib import Path

from .llm import DemoModel, Ollama
from .pipeline import run
from .report import save


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m debtagent.cli")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="measure, evaluate, classify, explain, decide")
    r.add_argument("--repo", default="demo_repo", help="folder of the Python code to evaluate")
    r.add_argument("--rules", default="debt_rules.json")
    r.add_argument("--architecture", default="examples/architecture.md")
    r.add_argument("--model", default="demo", help="demo, or an Ollama model such as qwen2.5-coder:1.5b")
    a = p.parse_args(argv)
    rules = json.loads(Path(a.rules).read_text(encoding="utf-8"))
    architecture = Path(a.architecture).read_text(encoding="utf-8") if Path(a.architecture).exists() else ""
    model = DemoModel() if a.model == "demo" else Ollama(a.model)
    report = run(a.repo, rules, architecture, model)
    folder = save(report)
    print(f"Report saved: {folder}")
    print(f"Recommendation: {report.decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
