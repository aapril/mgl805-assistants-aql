#!/usr/bin/env bash
# Collects the evidence of a laboratory repository in the isolated container,
# with the same options as the PR Evidence Checks workflow (Figure 5.4).
# Usage: lab/collect-evidence.sh <repository> <output folder>
set -euo pipefail
repo="$(cd "${1:?repository required}" && pwd)"
mkdir -p "${2:?output folder required}"
out="$(cd "$2" && pwd)"
chmod 0777 "$out"
docker run --rm --network=none --read-only \
  --cap-drop=ALL --security-opt=no-new-privileges \
  --pids-limit=256 --memory=4g --cpus=2 \
  --tmpfs /tmp:rw,nosuid,size=2g \
  --mount "type=bind,src=$repo,dst=/source,readonly" \
  --mount "type=bind,src=$out,dst=/out" \
  ai-review-runner:local sh -c \
  'cp -R /source /tmp/repo && python scripts/collect_evidence.py --repo /tmp/repo --out /out/evidence.json --run-tests --coverage-source example_app --scan-path example_app' >/dev/null
echo "Evidence written: $out/evidence.json"
