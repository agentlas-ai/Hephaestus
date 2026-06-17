from agentlas_cloud.networking import init_networking, route_request, save_card
from agentlas_cloud.networking.pipeline import detect_stages, plan_pipeline
from test_network_cards import make_ready_card


def test_detect_stages_is_plan_anchored():
    assert [k for k, _ in detect_stages("웹앱 기획부터 구현까지 해줘")] == ["plan", "build"]
    assert [k for k, _ in detect_stages("plan the PRD then implement and test it")] == ["plan", "build", "verify"]
    # build+verify without a plan anchor or explicit phrase → not a pipeline
    assert detect_stages("코드 구현하고 테스트 돌려줘") == []
    # explicit end-to-end phrase lifts the plan-anchor requirement
    assert [k for k, _ in detect_stages("구현하고 테스트까지 끝까지 해줘")] == ["build", "verify"]
    # single intent never decomposes
    assert detect_stages("웹사이트 만들어줘") == []


def pipeline_home(tmp_path):
    home = tmp_path / "networking"
    init_networking(home)
    planner = make_ready_card(
        tmp_path,
        "prd-team",
        triggers_ko=["서비스 기획 문서 잡아줘", "요구사항 스펙 정리"],
        triggers_en=["write a product spec", "draft requirements", "prd please"],
        antis=["legal contract", "photo retouch", "stock briefing"],
        capabilities=["draft_product_specs"],
    )
    planner["produces"] = [{"kind": "prd"}]
    builder = make_ready_card(
        tmp_path,
        "dev-team",
        triggers_ko=["웹앱 구현해줘", "사이트 개발 작업"],
        triggers_en=["implement the web app", "develop the website", "build the site"],
        antis=["legal contract", "photo retouch", "stock briefing"],
        capabilities=["implement_web_apps"],
    )
    builder["produces"] = [{"kind": "codebase_change"}]
    builder["consumes"] = [{"kind": "prd", "required": False}]
    qa = make_ready_card(
        tmp_path,
        "qa-team",
        triggers_ko=["회귀 테스트 돌려줘", "보안 점검 검증"],
        triggers_en=["run the regression tests", "verify the build", "qa pass"],
        antis=["legal contract", "photo retouch", "stock briefing"],
        capabilities=["run_regression_tests"],
    )
    qa["produces"] = [{"kind": "qa_report"}]
    qa["consumes"] = [{"kind": "codebase_change", "required": False}]
    for card in (planner, builder, qa):
        save_card(home, card)
    return home


def test_plan_pipeline_chains_by_artifacts(tmp_path):
    home = pipeline_home(tmp_path)
    from agentlas_cloud.networking.card_store import load_global_cards

    cards, _ = load_global_cards(home)
    plan = plan_pipeline("기획부터 구현하고 테스트까지 끝까지", cards, lambda card: 0.0)
    assert plan is not None
    kinds = [stage["produces"][0] for stage in plan["stages"]]
    assert kinds == ["prd", "codebase_change", "qa_report"]
    assert plan["stages"][1]["consumes"] == ["prd"]
    assert plan["stages"][2]["consumes"] == ["codebase_change"]
    ids = [stage["card"] for stage in plan["stages"]]
    assert len(set(ids)) == 3


def test_route_returns_pipeline_plan(tmp_path):
    home = pipeline_home(tmp_path)
    result = route_request("웹앱 기획부터 구현, 테스트 검증까지 끝까지 해줘", home=home, use_hub=False)
    assert result["action"] == "pipeline"
    kinds = [stage["produces"][0] for stage in result["stages"]]
    assert kinds == ["prd", "codebase_change", "qa_report"]
    assert result["handoff_dir"].startswith(".agentlas/pipeline/")
    assert result["receipt_id"]
    assert result["match_reason"].startswith("pipeline_")
    assert isinstance(result.get("graph_path"), list)
    assert isinstance(result.get("allowed_by"), list) and result["allowed_by"]
    assert result["blocked_by_axiom"] == []


def test_single_intent_is_not_decomposed(tmp_path):
    home = pipeline_home(tmp_path)
    result = route_request("웹앱 구현해줘", home=home, use_hub=False)
    assert result["action"] != "pipeline"
