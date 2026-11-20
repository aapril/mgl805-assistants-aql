"""CLI: demonstration, GitHub PR review, and publication."""
import argparse
import hashlib
import os
from pathlib import Path

from .config import required
from .connectors import GitHub, fetch_context
from .llm import DemoModel, Ollama
from .models import Context, Review
from .orchestrator import run
from .report import save
from .publish import publish
from .ci import read_evidence


def client():
    return GitHub(
        os.getenv("GITHUB_API_URL", "https://api.github.com"),
        required("GITHUB_TOKEN"),
        os.getenv("GITHUB_API_VERSION", "2026-03-10"),
    )


def local_context(args):
    """Builds a review context from files, for the laboratory; nothing is sent to GitHub."""
    text = args.issue_file.read_text(encoding="utf-8")
    title, _, body = text.partition("\n")
    diff = args.diff.read_text(encoding="utf-8")
    evidence = read_evidence(args.evidence) if args.evidence else None
    head = evidence.head_sha if evidence else hashlib.sha1(diff.encode()).hexdigest()
    return Context(
        issue_id=1, issue_subject=title.lstrip("# ").strip(), issue_description=body.strip(),
        issue_updated_at="local", repository="local/laboratory", pr=1,
        head_sha=head, base_sha=hashlib.sha1(text.encode()).hexdigest(),
        pr_title=title.lstrip("# ").strip(), diff=diff,
        standards=args.standards.read_text(encoding="utf-8") if args.standards else "",
        evidence=evidence,
        warnings=["Local run: the review is not tied to a GitHub pull request.",
                  "Diff-only analysis: unchanged files, binaries, and repository context were not inspected."],
    )


def local_model(name):
    if name == "demo":
        return DemoModel()
    return Ollama(os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"), name,
                  int(os.getenv("OLLAMA_TIMEOUT", "480")))


def main():
    parser = argparse.ArgumentParser(description="GitHub PR review by seven AI agents")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Simulation without external services")
    demo.add_argument("--out", type=Path, default=Path("runs"))
    review = sub.add_parser("review", help="Read the PR and its GitHub issue, then run seven agents")
    review.add_argument("--issue", type=int, help="Optional if the PR contains 'Closes #12'")
    review.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"), help="owner/repo; automatic in Actions")
    review.add_argument("--pr", type=int, required=True)
    review.add_argument("--evidence", type=Path)
    review.add_argument("--standards", type=Path)
    review.add_argument("--out", type=Path, default=Path("runs"))
    review.add_argument("--publish", action="store_true", help="Publish or update the summary on the PR")
    local = sub.add_parser("local", help="Review an issue file and a diff file, without GitHub")
    local.add_argument("--issue-file", type=Path, required=True, help="Markdown file: first line is the title")
    local.add_argument("--diff", type=Path, required=True, help="Unified diff (git diff or .patch)")
    local.add_argument("--evidence", type=Path)
    local.add_argument("--standards", type=Path)
    local.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
                       help="Ollama model name, or 'demo' for the simulated model")
    local.add_argument("--out", type=Path, default=Path("runs"))
    pub = sub.add_parser("publish", help="Publish an existing report on the PR")
    pub.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "demo":
            context = Context(
                issue_id=42, issue_subject="Safe division",
                issue_description="AC-1: a zero divisor raises ValueError.",
                issue_updated_at="2026-10-04T00:00:00Z",
                repository="demo/calculator", pr=1,
                head_sha="a" * 40, base_sha="b" * 40, pr_title="Handle division by zero",
                diff="diff --git a/calculator.py b/calculator.py\n--- a/calculator.py\n+++ b/calculator.py\n@@ -1,2 +1,4 @@\n def divide(a, b):\n+    if b == 0:\n+        raise ValueError('division by zero')\n     return a / b\n",
                demo=True,
            )
            print(save(run(context, DemoModel()), args.out))
        elif args.command == "review":
            if not args.repo:
                raise ValueError("--repo is required outside GitHub Actions")
            git = client()
            evidence = read_evidence(args.evidence) if args.evidence else None
            standards = args.standards.read_text(encoding="utf-8") if args.standards else ""
            context = fetch_context(git, args.repo, args.pr, args.issue, standards, evidence)
            model = Ollama(
                os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
                os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b"),
                int(os.getenv("OLLAMA_TIMEOUT", "480")),
            )
            report = run(context, model)
            dest = save(report, args.out)
            print(f"Report saved: {dest}", flush=True)
            if args.publish:
                publish(report, git, dest / "publication.json")
                print("Summary published on the GitHub PR.", flush=True)
            if any(r.status == "incomplete" for r in report.results):
                print("At least one agent failed; the review is incomplete.")
                return 2
        elif args.command == "local":
            context = local_context(args)
            context.demo = args.model == "demo"
            report = run(context, local_model(args.model))
            dest = save(report, args.out)
            print(f"Report saved: {dest}", flush=True)
            print(f"Recommendation: {report.decision}", flush=True)
            if any(r.status == "incomplete" for r in report.results):
                print("At least one agent failed; the review is incomplete.")
                return 2
        elif args.command == "publish":
            report = Review.model_validate_json(args.report.read_text(encoding="utf-8"))
            publish(report, client(), args.report.parent / "publication.json")
            print("Summary published on GitHub.")
        return 0
    except Exception as exc:
        from .security import redact
        print(f"Error {type(exc).__name__}: {redact(str(exc))[:500]}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
