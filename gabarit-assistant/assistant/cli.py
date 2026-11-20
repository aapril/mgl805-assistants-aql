"""Command line: collect the evidence, then run the assistant (companion guide, Section 14)."""
import argparse
import json
import sys
from pathlib import Path
from .artifact import load
from .contracts import Evidence
from .evidence import collect
from .llm import DemoModel, Ollama
from .pipeline import run
from .report import save


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m assistant.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect", help="run the deterministic tools and save the evidence")
    c.add_argument("--config", default="assistant_config.json")
    c.add_argument("--artifact", nargs="+", required=True)
    c.add_argument("--out", default="evidence.json")
    r = sub.add_parser("run", help="run the agents and the decision rule")
    r.add_argument("--config", default="assistant_config.json")
    r.add_argument("--reference", required=True)
    r.add_argument("--artifact", nargs="+", required=True)
    r.add_argument("--evidence")
    r.add_argument("--model", default="demo", help="demo, or the name of an Ollama model")
    args = parser.parse_args(argv)
    if args.command == "collect":
        evidence = collect(args.config, args.artifact)
        Path(args.out).write_text(evidence.model_dump_json(indent=2), encoding="utf-8")
        for t in evidence.tools:
            print(f"{t.name}: {t.status}")
        print(f"Evidence saved: {args.out}")
        return 0
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    evidence = Evidence.model_validate_json(Path(args.evidence).read_text(encoding="utf-8")) if args.evidence else None
    model = DemoModel() if args.model == "demo" else Ollama(args.model)
    report = run(config["assistant"], Path(args.reference).read_text(encoding="utf-8"),
                 load(args.artifact), evidence, model)
    folder = save(report)
    print(f"Report saved: {folder}")
    print(f"Recommendation: {report.decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
