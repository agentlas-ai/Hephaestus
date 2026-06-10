#!/usr/bin/env bash
# Behavioral verification for the ontology proposal agent reference (B-3/C-2).
# Checks runtime behavior, not just file existence.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
DB="$WORK/ontology.sqlite"
export PYTHONPATH="$REPO_ROOT"

fail() { echo "FAIL: $1" >&2; exit 1; }

# 1. ingest: Korean corpus loads and produces chunks
python3 -m ontology --db "$DB" ingest "$HERE/.agentlas/ontology-inbox" --scope internal > "$WORK/ingest.json"
python3 - "$WORK/ingest.json" << 'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
assert payload["chunks_written"] >= 2, payload
PY

# 2. retrieve: Korean query returns chunks with source spans (citation material)
python3 -m ontology --db "$DB" query "납품 일정 제안" > "$WORK/query.json"
python3 - "$WORK/query.json" << 'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
assert payload["chunks"], "Korean retrieval returned no chunks"
top = payload["chunks"][0]
assert top.get("source_id") and top.get("source_span"), "chunks must carry source refs"
assert "납품" in top["text"], top["text"][:80]
PY

# 3. privacy gate behavior: private-scope docs are excluded from default scopes
echo "비공개 단가표: 핵심 모듈 단가는 협상 대상." > "$WORK/private-pricing.md"
python3 -m ontology --db "$DB" ingest "$WORK/private-pricing.md" --scope private > /dev/null
python3 -m ontology --db "$DB" query "핵심 모듈 단가" > "$WORK/blocked.json"
python3 - "$WORK/blocked.json" << 'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
texts = " ".join(chunk["text"] for chunk in payload["chunks"])
assert "단가는 협상 대상" not in texts, "private scope leaked into default query"
PY

# 4. wiring: loop_policy + injected contracts resolve to real templates
grep -q "loop_policy: verified" "$HERE/agent.md" || fail "agent.md missing loop_policy: verified"
python3 - "$HERE/.agentlas/injected-contracts.json" "$REPO_ROOT" << 'PY'
import json, sys
from pathlib import Path
payload = json.load(open(sys.argv[1]))
repo = Path(sys.argv[2])
assert payload["loop_policy"] == "verified"
assert "super-ontology-side-effect-containment" in payload["contracts"]
for contract in payload["contracts"]:
    tpl = repo / "templates" / f"{contract}.json.tpl"
    tpl_jsonl = repo / "templates" / f"{contract}.jsonl.tpl"
    assert tpl.exists() or tpl_jsonl.exists(), f"unknown contract template: {contract}"
PY

# 5. runtime verify passes
python3 -m ontology --db "$DB" verify > "$WORK/verify.json"
python3 - "$WORK/verify.json" << 'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
assert payload["status"] == "pass", payload
PY

echo "ontology-proposal-agent verify: PASS"
