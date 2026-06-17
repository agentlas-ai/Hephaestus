import json
import os
import subprocess
from pathlib import Path

from agentlas_cloud.networking import init_networking, save_card
from agentlas_cloud.networking.bootstrap import atomic_write_json
from test_network_cards import make_ready_card


ROOT = Path(__file__).resolve().parents[1]


def _run_hephaestus(args, *, home, cwd=ROOT):
    env = os.environ.copy()
    env["AGENTLAS_NETWORKING_HOME"] = str(home)
    env["HEPHAESTUS_UPDATE_CHECK"] = "0"
    completed = subprocess.run(
        [str(ROOT / "bin" / "hephaestus"), *args],
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout)


def _disable_hub_for_overwhelming_local(home):
    atomic_write_json(
        home / "policies" / "routing-policy.json",
        {
            "schemaVersion": "2.0",
            "t_high": 4.5,
            "t_low": 3.0,
            "margin": 0.8,
            "min_ready_cards": 1,
            "max_hops": 2,
            "clarify_max_candidates": 3,
            "multi_route": False,
        },
    )


def _write_minimal_ao_graph(project, agents):
    ontology = project / ".agentlas" / "agent-ontology"
    ontology.mkdir(parents=True)
    (ontology / "agents.jsonl").write_text(
        "\n".join(json.dumps(agent, ensure_ascii=False) for agent in agents) + "\n",
        encoding="utf-8",
    )
    (ontology / "artifacts.jsonl").write_text("", encoding="utf-8")
    (ontology / "edges.jsonl").write_text("", encoding="utf-8")
    (ontology / "capabilities.json").write_text(
        json.dumps({"capabilities": ["run_regression_tests"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_hephaestus_shorthand_routes_like_at_hephaestus(tmp_path):
    home = tmp_path / "networking"
    init_networking(home)
    _disable_hub_for_overwhelming_local(home)
    card = make_ready_card(
        tmp_path,
        "insta-team",
        triggers_ko=["인스타그램 마케팅 콘텐츠 만들어줘", "인스타 릴스 캠페인 기획해줘"],
        triggers_en=["create instagram marketing content", "plan an instagram reels campaign", "instagram growth plan"],
        antis=["legal contract review", "ios testflight deploy", "database schema design"],
        capabilities=["plan_instagram_content", "write_marketing_captions"],
    )
    save_card(home, card)

    result = _run_hephaestus(["create instagram marketing content"], home=home)

    assert result["action"] == "route"
    assert result["selected"]["id"] == "local/insta-team"
    assert result["receipt_id"]
    assert result["match_reason"] == "local_confident"


def test_hephaestus_route_caller_option_enforces_ao_gate(tmp_path):
    home = tmp_path / "networking"
    init_networking(home)
    target = make_ready_card(
        tmp_path,
        "target-agent",
        triggers_ko=["회귀 테스트 실행", "품질 검증"],
        triggers_en=["run regression tests", "verify the build", "qa pass"],
        antis=["instagram content", "legal contract", "payment"],
        capabilities=["run_regression_tests"],
    )
    save_card(home, target)

    project = tmp_path / "project"
    _write_minimal_ao_graph(
        project,
        [
            {"id": "local/caller-agent", "type": "Specialist", "name": "Caller"},
            {"id": "local/target-agent", "type": "Specialist", "name": "Target"},
        ],
    )

    result = _run_hephaestus(
        [
            "route",
            "run regression tests",
            "--project",
            str(project),
            "--no-hub",
            "--caller",
            "local/caller-agent",
        ],
        home=home,
    )

    assert result["action"] == "propose_new"
    assert result["selected"] is None
    assert result["fallback_scope"] == "local_graph_and_caller_gate"
    assert result["blocked_by_axiom"] == [
        "deny rule matched: local/caller-agent -> routes_to -> local/target-agent"
    ]
