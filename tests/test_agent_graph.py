import json
from pathlib import Path

from agentlas_cloud.agent_graph import (
    describe_graph,
    diff_ontology,
    execute_query,
    load_graph,
    migrate_ontology,
    plan_path,
    validate_graph,
)


def _seed_ao_fixtures(root: Path) -> None:
    base = root / ".agentlas"
    base.mkdir(exist_ok=True, parents=True)
    (base / "company-blueprint.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "00-orchestrator",
                        "role": "Orchestrator",
                        "member_of": "platform",
                    },
                    {"id": "10-specialist-a", "role": "Specialist", "member_of": "platform"},
                ],
                "edges": [
                    {"from": "00-orchestrator", "to": "10-specialist-a", "handoff": "delegate"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (base / "routing-card.json").write_text(
        json.dumps(
            {
                "id": "local/10-specialist-a",
                "name": "Specialist A",
                "capabilities": ["implement_web_apps", "run_regression_tests"],
                "produces": [{"kind": "codebase_change"}, {"kind": "prd"}],
                "consumes": [{"kind": "design_docs"}, {"kind": "codebase_change"}],
                "routing_status": "trusted",
                "entrypoints": {"canonical_command": "build-web"},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (base / "sitemap.json").write_text(
        json.dumps(
            {
                "edges": [
                    {"from": "local/10-specialist-a", "to": "local/qa-team", "label": "delegates"},
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (base / "memory-map.json").write_text(
        json.dumps({"writeOwners": {"project": "10-specialist-a"}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_ao_migrate_and_load_graph(tmp_path: Path) -> None:
    _seed_ao_fixtures(tmp_path)
    report = migrate_ontology(tmp_path, write=True, overwrite=True)
    assert report["status"] == "ok"
    assert report["counts"]["agents"] >= 2
    assert report["counts"]["artifacts"] >= 2

    graph = load_graph(tmp_path)
    assert graph["path"] == str((tmp_path / ".agentlas" / "agent-ontology").resolve())
    assert graph["counts"]["agents"] == report["counts"]["agents"]
    assert any(agent["id"] == "00-orchestrator" for agent in graph["graph"]["agents"])
    assert any(artifact["id"].startswith("artifact:codebase_change") for artifact in graph["graph"]["artifacts"])


def test_ao_validate_blocked_relation_and_drift(tmp_path: Path) -> None:
    _seed_ao_fixtures(tmp_path)
    migrate_ontology(tmp_path, write=True, overwrite=True)

    # Add a policy-breaking Specialist->Specialist route and ensure the violation is reported.
    ontology_root = tmp_path / ".agentlas" / "agent-ontology"
    existing_edges = []
    edge_file = ontology_root / "edges.jsonl"
    if edge_file.exists():
        existing_edges = [line for line in edge_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    extra_edges = [
        {"from": "10-specialist-a", "to": "10-specialist-a", "relation": "routes_to", "kind": "migrated"}
    ]
    edge_payload = existing_edges + [json.dumps(edge) for edge in extra_edges]
    edge_file.write_text("\n".join(edge_payload) + "\n", encoding="utf-8")

    validation = validate_graph(tmp_path)
    # A deny-violating edge is now a hard error: lint must fail (plan §2.3).
    assert validation["valid"] is False
    assert any("deny-violating edge" in err for err in validation["errors"])
    assert validation["blocked_edges"]
    assert validation["counts"]["edges"] >= len(extra_edges)

    diff = diff_ontology(tmp_path)
    assert diff["status"] == "drift"


def test_ao_query_and_plan_path(tmp_path: Path) -> None:
    _seed_ao_fixtures(tmp_path)
    migrate_ontology(tmp_path, write=True, overwrite=True)
    summary = describe_graph(tmp_path)
    assert summary["counts"]["agents"] >= 2

    # Produce/consume style query should find the specialist card by artifact.
    query = execute_query("type:Specialist and produces:codebase_change", tmp_path)
    assert query["count"] >= 1
    assert query["matches"][0]["type"] == "Specialist"

    route = plan_path(tmp_path, "00-orchestrator", "10-specialist-a", relation="delegates_to")
    assert route["found"] is True
    assert route["edges"][0]["from"] == "00-orchestrator"
    assert route["edges"][0]["to"] == "10-specialist-a"


def test_ao_diff_smoke(tmp_path: Path) -> None:
    _seed_ao_fixtures(tmp_path)
    migrate_ontology(tmp_path, write=True, overwrite=True)
    drift = diff_ontology(tmp_path)
    assert drift["status"] == "clean"
    assert set(drift["counts"]) == {"agents", "artifacts", "capabilities", "edges"}


def test_ao_a2a_import_aligns_without_can_invoke(tmp_path: Path) -> None:
    from agentlas_cloud.agent_graph import import_agent_card

    card = {
        "name": "Acme Research Agent",
        "url": "https://acme.example/agent",
        "skills": [
            {"id": "s1", "name": "Team Builder", "tags": ["build_agent_team"]},
            {"id": "s2", "name": "Maker", "tags": ["create_single_agent", "totally_unknown_capability"]},
        ],
    }
    report = import_agent_card(card, project_root=tmp_path)

    assert report["external_agent"]["type"] == "ExternalAgent"
    assert report["external_agent"]["id"].startswith("external:")
    assert report["can_invoke"] is False
    # Every emitted edge is an alignment edge — never a can_invoke edge.
    assert report["edges"], "expected at least one aligned_with edge"
    assert all(edge["relation"] == "aligned_with" for edge in report["edges"])
    assert not any(edge["relation"] == "can_invoke" for edge in report["edges"])
    aligned_caps = {a["capability"] for a in report["aligned"]}
    assert {"build_agent_team", "create_single_agent"} <= aligned_caps
    assert "totally_unknown_capability" in report["unaligned"]


def test_ao_a2a_export_redacts_private_fields(tmp_path: Path) -> None:
    from agentlas_cloud.agent_graph import WELL_KNOWN_PATH, export_agent_card

    _seed_ao_fixtures(tmp_path)
    migrate_ontology(tmp_path, write=True, overwrite=True)

    result = export_agent_card(project_root=tmp_path, agent_id="local/10-specialist-a")
    assert "error" not in result
    card = result["agent_card"]
    assert result["leaked_private_fields"] == []
    assert result["well_known_path"] == WELL_KNOWN_PATH
    # Public card must not carry private internal fields.
    for forbidden in ("path", "entrypoints", "memory_behavior", "source", "risk_profile"):
        assert forbidden not in card
    skill_ids = {s["id"] for s in card["skills"]}
    assert "implement_web_apps" in skill_ids


def test_ao_can_invoke_requires_alignment_else_lint_fails(tmp_path: Path) -> None:
    """ExternalAgent can_invoke without aligned_with must FAIL lint (require-rule)."""
    _seed_ao_fixtures(tmp_path)
    migrate_ontology(tmp_path, write=True, overwrite=True)

    ontology_root = tmp_path / ".agentlas" / "agent-ontology"
    agents_file = ontology_root / "agents.jsonl"
    agents_lines = [line for line in agents_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    agents_lines.append(json.dumps({"id": "external:foo", "type": "ExternalAgent", "name": "Foo"}))
    agents_lines.append(json.dumps({"id": "external:bar", "type": "ExternalAgent", "name": "Bar"}))
    agents_file.write_text("\n".join(agents_lines) + "\n", encoding="utf-8")

    edges_file = ontology_root / "edges.jsonl"
    edges_lines = [line for line in edges_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    edges_lines.append(json.dumps({"from": "external:foo", "to": "external:bar", "relation": "can_invoke", "kind": "can_invoke"}))
    edges_file.write_text("\n".join(edges_lines) + "\n", encoding="utf-8")

    validation = validate_graph(tmp_path)
    assert validation["valid"] is False
    assert validation["require_violations"], "can_invoke without aligned_with must raise a require violation"
    assert any("can_invoke" in str(v.get("edge")) for v in validation["require_violations"])


def test_ao_a2a_import_rejects_non_dict() -> None:
    from agentlas_cloud.agent_graph import import_agent_card

    result = import_agent_card("not-a-card")
    assert "error" in result
    assert result["can_invoke"] is False


def test_ao_a2a_import_caps_huge_skill_lists(tmp_path: Path) -> None:
    from agentlas_cloud.agent_graph import import_agent_card

    card = {
        "name": "Flood",
        "skills": [{"id": f"s{i}", "tags": ["build_agent_team"]} for i in range(5000)],
    }
    report = import_agent_card(card, project_root=tmp_path)
    assert report["can_invoke"] is False
    assert any("truncated" in w for w in report.get("warnings", []))
    # Despite the flood, alignment still works and stays bounded.
    assert {a["capability"] for a in report["aligned"]} == {"build_agent_team"}
