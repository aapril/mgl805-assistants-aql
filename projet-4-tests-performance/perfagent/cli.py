"""Command line: start the demo application, or run the performance agent."""
import argparse
import json
import sys
from pathlib import Path
from . import slo as slo_mod
from .llm import DemoModel, Ollama
from .pipeline import run
from .report import save


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m perfagent.cli")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("demo-app", help="start the demo application with seeded defects")
    d.add_argument("--port", type=int, default=8099)
    r = sub.add_parser("run", help="plan, measure, evaluate, explain, decide")
    r.add_argument("--target", default="http://127.0.0.1:8099")
    r.add_argument("--config", default="perf_config.json")
    r.add_argument("--requirements", default="examples/requirements.md")
    r.add_argument("--slo", default="examples/slo.json")
    r.add_argument("--model", default="demo", help="demo, or an Ollama model such as qwen2.5-coder:1.5b")
    a = p.parse_args(argv)
    if a.command == "demo-app":
        from demo_app.app import serve
        server = serve(a.port)
        print(f"Demo application on http://127.0.0.1:{a.port} (Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0
    config = json.loads(Path(a.config).read_text(encoding="utf-8"))
    model = DemoModel() if a.model == "demo" else Ollama(a.model)
    report = run(config, Path(a.requirements).read_text(encoding="utf-8"), slo_mod.load(a.slo), a.target, model)
    folder = save(report)
    print(f"Report saved: {folder}")
    print(f"Recommendation: {report.decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
