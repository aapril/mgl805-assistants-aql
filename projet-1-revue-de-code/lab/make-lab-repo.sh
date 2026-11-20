#!/usr/bin/env bash
# Builds the application under review for the laboratory of Chapter 5.
# Usage: lab/make-lab-repo.sh <destination> [subtract|forged]
#   subtract  applies the pull request of the worked example (book Section 5.3.1.5; guide Section 7) (default);
#   forged    also adds the conftest.py of book Section 5.4.2 (guide Section 9), which forges the test evidence.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
dest="${1:?destination folder required}"
scenario="${2:-subtract}"
if [[ -e "$dest" ]]; then
  echo "Destination $dest already exists; choose another folder or delete it." >&2
  exit 1
fi
mkdir -p "$dest/tests" "$dest/example_app"
cp "$here"/example_app/*.py "$dest/example_app/"
cp "$here/tests/test_calculator.py" "$dest/tests/"
cd "$dest"
printf '__pycache__/\n.pytest_cache/\n.coverage\n' > .gitignore
git init -q -b main
git add .
git -c user.name="Lab" -c user.email="lab@example.com" commit -qm "Calculator with safe division"
git apply "$here/lab/pr-subtract.patch"
if [[ "$scenario" == "forged" ]]; then
  cp "$here/lab/forged-evidence/conftest.py.txt" conftest.py
  cp "$here/lab/forged-evidence/test_regression.py.txt" tests/test_regression.py
fi
git add .
git -c user.name="Lab" -c user.email="lab@example.com" commit -qm "Pull request under review ($scenario)"
git diff HEAD~1 HEAD > pull-request.diff
mv pull-request.diff ../"$(basename "$dest")".diff
echo "Repository ready: $dest (HEAD $(git rev-parse --short HEAD))"
echo "Diff of the pull request: $(cd .. && pwd)/$(basename "$dest").diff"
