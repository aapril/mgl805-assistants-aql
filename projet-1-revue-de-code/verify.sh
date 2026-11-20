#!/usr/bin/env bash
# Verifies the commands and results of the companion guide of Chapter 5 on your computer.
# Requires: Python 3.11 or later with the package installed (pip install -e ".[lab]"), Git, Docker.
# Optional: a running Ollama server with the model, for the last check (set RUN_MODEL=1).
set -uo pipefail
cd "$(dirname "$0")"
ok=0; bad=0
check() { if eval "$2"; then echo "OK    $1"; ok=$((ok+1)); else echo "FAIL  $1"; bad=$((bad+1)); fi; }
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

out="$(python -m unittest discover -s tests 2>&1)"
check "65 unit tests of the reviewer pass" '[[ "$out" == *"Ran 65 tests"* && "$out" == *"OK"* ]]'
demo="$(python -m review.cli demo --out "$work/runs-demo")"
check "the demonstration produces a report" '[[ -f "$demo/report.md" ]] && grep -q "human_review_required" "$demo/report.md"'

check "the runner image builds" 'docker build -q -f Dockerfile.runner -t ai-review-runner:local . >/dev/null'
lab/make-lab-repo.sh "$work/subtract" subtract >/dev/null
lab/make-lab-repo.sh "$work/forged" forged >/dev/null

collect() { lab/collect-evidence.sh "$1" "$2" >/dev/null; }
collect "$work/subtract" "$work/ev-subtract"
collect "$work/forged" "$work/ev-forged"
sha_s="$(git -C "$work/subtract" rev-parse HEAD)"; sha_f="$(git -C "$work/forged" rev-parse HEAD)"
check "evidence is tied to the commit under review" 'python -m review.ci normalize --input "$work/ev-subtract/evidence.json" --head "$sha_s" --output "$work/subtract.json" >/dev/null'
python -m review.ci normalize --input "$work/ev-forged/evidence.json" --head "$sha_f" --output "$work/forged.json" >/dev/null
check "subtract: pytest passed, 5 cases, coverage 90%" 'python lab/expect.py "$work/subtract.json" "pytest=5 cases, 0 failures, 0 skipped" coverage=90.0'
check "subtract: Ruff, Bandit, and Gitleaks pass" 'python lab/expect.py "$work/subtract.json" ruff=passed bandit=passed gitleaks=passed'
check "forged: the false test is reported as passed (6 cases, 0 failures)" 'python lab/expect.py "$work/forged.json" "pytest=6 cases, 0 failures, 0 skipped"'
check "forged: without conftest.py, the same test fails" '(cd "$work/forged" && ! python -m pytest -q -p no:cacheprovider --noconftest >/dev/null 2>&1)'
check "subtract: the gate accepts the evidence" 'python -m review.ci gate --input "$work/subtract.json" --head "$sha_s" >/dev/null'
loc="$(python -m review.cli local --issue-file lab/issue-subtract.md --diff "$work/subtract.diff" --evidence "$work/subtract.json" --model demo --out "$work/runs-local" | tail -1)"
check "local review with the simulated model" '[[ "$loc" == "Recommendation: human_review_required" ]]'

if [[ "${RUN_MODEL:-0}" == "1" ]]; then
  model="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
  echo "Running the seven agents with $model; this can take 10 to 20 minutes on a CPU..."
  python -m review.cli local --issue-file lab/issue-subtract.md --diff "$work/subtract.diff" \
    --evidence "$work/subtract.json" --model "$model" --out runs | tee "$work/model.txt"
  check "real model: seven complete agents and a recommendation" 'grep -q "^Recommendation: " "$work/model.txt" && ! grep -q "incomplete" "$work/model.txt"'
fi
echo "$ok checks passed, $bad deviations"
[[ $bad -eq 0 ]]
