#!/usr/bin/env bash
# C-4: MCP surface preservation. The agentlas Hub MCP server registration
# (tool transport + URL) must stay consistent across every runtime surface;
# improvements to search/builders must not break the natural-language MCP
# interface.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

expected_url="https://agentlas.cloud/api/mcp/v1"

fail() {
  echo "verify-mcp-surface: $*" >&2
  exit 1
}

# 1. Claude Code: bundled .mcp.json registers the HTTP server
python3 - "$expected_url" <<'PY' || fail "claude plugin .mcp.json contract broken"
import json, sys
expected = sys.argv[1]
data = json.load(open("claude/plugins/agentlas-core-engine-meta-agent/.mcp.json"))
server = data.get("agentlas") or {}
assert server.get("type") == "http", data
assert server.get("url") == expected, data
PY

# 2. Gemini: extension manifest registers the same server
python3 - "$expected_url" <<'PY' || fail "gemini extension MCP contract broken"
import json, sys
expected = sys.argv[1]
data = json.load(open("gemini/extension/gemini-extension.json"))
server = (data.get("mcpServers") or {}).get("agentlas") or {}
assert server.get("httpUrl") == expected, data
PY

# 3. Codex + Antigravity: install script registers the same default URL
grep -q "AGENTLAS_MCP_URL:-$expected_url" scripts/install-all-runtimes.sh \
  || fail "install-all-runtimes.sh default MCP URL changed"
grep -q '\[mcp_servers\.agentlas\]' scripts/install-all-runtimes.sh \
  || fail "codex MCP registration block missing"
grep -q 'register_antigravity_mcp' scripts/install-all-runtimes.sh \
  || fail "antigravity MCP registration missing"

# 4. Ontology runtime output contract: the keys the MCP/natural-language
#    surface relies on must stay present (additive changes only).
PYTHONPATH="$root" python3 <<'PY' || fail "ontology query/verify output contract broken"
import tempfile
from pathlib import Path
from ontology import OntologyRuntime, RuntimeConfig

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    doc = root / "doc.md"
    doc.write_text("Surface Probe depends on Contract Check.", encoding="utf-8")
    rt = OntologyRuntime(RuntimeConfig(db_path=root / "db.sqlite"))
    rt.ingest_path(doc, access_scope="internal")
    answer = rt.query("Surface Probe")
    for key in ("query", "chunks", "related_entities", "relation_edges",
                "memory_candidate_suggestions", "working_memory", "vector_adapter"):
        assert key in answer, f"query output lost key: {key}"
    report = rt.verify()
    for key in ("status", "schema_version", "counts", "storage_adapter", "vector_adapter"):
        assert key in report, f"verify output lost key: {key}"
PY

echo "MCP surface verification passed."
