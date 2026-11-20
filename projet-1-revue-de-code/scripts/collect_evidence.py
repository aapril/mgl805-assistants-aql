"""Run in a disposable environment, without any token or secret.

The tools are launched with fixed arguments and a maximum duration.
pytest runs only with --run-tests, because it executes the repository code.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from review.models import Evidence, Finding, ToolResult
from review.security import redact


def command(argv, cwd, timeout=180, extra_env=None):
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "TMPDIR")}
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra_env or {})
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode, result.stdout, result.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, "", type(exc).__name__


def git_state(repo):
    code, sha, _ = command(["git", "rev-parse", "HEAD"], repo)
    if code:
        raise ValueError("Git repository not found")
    code, status, _ = command(["git", "status", "--porcelain", "--untracked-files=all"], repo)
    if code or status.strip():
        raise ValueError("The repository must be clean, without untracked files")
    return sha.strip()


def location(path, repo):
    try:
        return str(Path(path).resolve().relative_to(repo))
    except ValueError:
        return str(path)


def finding(title, evidence, severity, file=None, line=None):
    return Finding(title=title[:200], evidence=redact(evidence)[:1500], severity=severity,
        file=file, line=line, source="tool", recommendation="Verify the finding, then correct it or document a justified exception.")


def test_counts(xml_text):
    if "<!DOCTYPE" in xml_text.upper() or "<!ENTITY" in xml_text.upper():
        raise ValueError("XML with an entity declaration refused")
    root = ET.fromstring(xml_text)
    cases = list(root.iter("testcase"))
    return len(cases), sum(c.find("failure") is not None or c.find("error") is not None for c in cases), sum(c.find("skipped") is not None for c in cases)


def collect(repo, run_tests=False, coverage_source=".", scan_path="."):
    repo = repo.resolve()
    target = (repo / scan_path).resolve()
    if not target.is_relative_to(repo) or not target.is_dir():
        raise ValueError("The scan folder must exist inside the repository")
    sha = git_state(repo)
    tools = {}
    coverage, counts = None, (0, 0, 0)
    with tempfile.TemporaryDirectory(prefix="review-evidence-") as tmp:
        work = Path(tmp)
        # Analyzer configuration files stay outside the repository under analysis.
        code, out, _ = command(["ruff", "check", "--isolated", "--select", "E4,E7,E9,F", "--output-format", "json", str(target)], work)
        try:
            rows = json.loads(out)
            if code not in (0, 1) or not isinstance(rows, list):
                raise ValueError()
            findings = [finding(f"Ruff {r['code']}", r["message"], "medium", location(r["filename"], repo), r["location"]["row"]) for r in rows[:100]]
            tools["ruff"] = ToolResult(status="failed" if code or rows else "passed", findings=findings, total_findings=len(rows))
        except (ValueError, KeyError, TypeError):
            tools["ruff"] = ToolResult(status="error", details="Ruff missing, in error, or invalid result")
        code, out, _ = command(["bandit", "-r", str(target), "-f", "json", "-q"], work)
        try:
            data = json.loads(out)
            if code not in (0, 1) or data.get("errors"):
                raise ValueError()
            rows = data["results"]
            findings = [finding(f"Bandit {r['test_id']}", r["issue_text"], r["issue_severity"].lower(), location(r["filename"], repo), r["line_number"]) for r in rows[:100]]
            tools["bandit"] = ToolResult(status="failed" if code or rows else "passed", findings=findings, total_findings=len(rows))
        except (ValueError, KeyError, TypeError):
            tools["bandit"] = ToolResult(status="error", details="Bandit missing, in error, or invalid result")
        config = work / "gitleaks.toml"
        config.write_text("[extend]\nuseDefault = true\n")
        ignore = work / "gitleaksignore"
        ignore.write_text("")
        output = work / "gitleaks.json"
        code, _, _ = command(["gitleaks", "dir", str(repo), "--config", str(config), "--gitleaks-ignore-path", str(ignore), "--redact=100", "--no-banner", "--report-format", "json", "--report-path", str(output)], work)
        try:
            if code not in (0, 1):
                raise ValueError()
            rows = json.loads(output.read_text())
            findings = [finding(f"Gitleaks {r['RuleID']}", "Potential secret detected; value deliberately omitted.", "high", r["File"], r["StartLine"]) for r in rows[:100]]
            tools["gitleaks"] = ToolResult(status="failed" if code or rows else "passed", findings=findings, total_findings=len(rows))
        except (ValueError, KeyError, TypeError, OSError):
            tools["gitleaks"] = ToolResult(status="error", details="Gitleaks missing, in error, or invalid result")
        tools["pytest"] = ToolResult(status="not_run", details="Enable --run-tests only in an isolated environment")
        if run_tests:
            junit, cov = work / "junit.xml", work / "coverage.json"
            code, _, _ = command([sys.executable, "-m", "pytest", "-p", "pytest_cov", "-p", "no:cacheprovider", "--junitxml=" + str(junit), "--cov=" + coverage_source, "--cov-report=json:" + str(cov)], repo, 300, {"COVERAGE_FILE": str(work / ".coverage")})
            try:
                counts = test_counts(junit.read_text())
                if code not in (0, 1):
                    raise ValueError()
                coverage = float(json.loads(cov.read_text())["totals"]["percent_covered"])
                tools["pytest"] = ToolResult(status="failed" if code or counts[1] else "passed", total_findings=counts[1], details=f"{counts[0]} cases, {counts[1]} failures, {counts[2]} skipped")
            except (ValueError, KeyError, TypeError, OSError, ET.ParseError):
                tools["pytest"] = ToolResult(status="error", details=f"Reports missing or invalid, or pytest exit code {code}")
        if git_state(repo) != sha:
            raise ValueError("The code changed during collection")
    return Evidence(head_sha=sha, generated_at=datetime.now(timezone.utc).isoformat(), tools=tools,
        coverage_percent=coverage, tests_run=counts[0], tests_failed=counts[1], tests_skipped=counts[2])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--coverage-source", default=".")
    parser.add_argument("--scan-path", default=".", help="Code folder to analyze with Ruff and Bandit, relative to the repository")
    args = parser.parse_args()
    if args.out.resolve().is_relative_to(args.repo.resolve()):
        raise SystemExit("Write evidence.json outside the repository under analysis")
    result = collect(args.repo, args.run_tests, args.coverage_source, args.scan_path)
    args.out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(args.out)
