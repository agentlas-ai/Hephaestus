import json

from agentlas_cloud.networking import init_networking, route_request, save_card
from agentlas_cloud.networking.bench import run_bench
from test_network_cards import make_ready_card


def setup_home(tmp_path):
    home = tmp_path / "networking"
    init_networking(home)
    insta = make_ready_card(
        tmp_path,
        "insta-team",
        triggers_ko=["인스타그램 마케팅 콘텐츠 만들어줘", "인스타 릴스 캠페인 기획해줘"],
        triggers_en=["create instagram marketing content", "plan an instagram reels campaign", "instagram growth plan"],
        antis=["legal contract review", "ios testflight deploy", "database schema design"],
        capabilities=["plan_instagram_content", "write_marketing_captions", "schedule_social_posts"],
    )
    legal = make_ready_card(
        tmp_path,
        "legal-review",
        triggers_ko=["계약서 검토해줘", "법률 계약 리스크 확인"],
        triggers_en=["review this contract", "check legal risks in the agreement", "contract clause analysis"],
        antis=["instagram content", "social media campaign", "image generation"],
        capabilities=["review_legal_contracts", "flag_contract_risks"],
    )
    save_card(home, insta)
    save_card(home, legal)
    return home


def test_routes_to_best_card(tmp_path):
    home = setup_home(tmp_path)
    result = route_request("인스타그램 마케팅 콘텐츠 만들어줘", home=home, use_hub=False)
    assert result["action"] == "route"
    assert result["selected"]["id"] == "local/insta-team"
    assert result["receipt_id"]
    ledger = (home / "ledgers" / "routing-decisions.jsonl").read_text(encoding="utf-8")
    assert "insta-team" in ledger
    assert "만들어줘" not in ledger  # raw prompt is never persisted verbatim


def test_english_query_routes_too(tmp_path):
    home = setup_home(tmp_path)
    result = route_request("review this contract for legal risks", home=home, use_hub=False)
    assert result["action"] == "route"
    assert result["selected"]["id"] == "local/legal-review"


def test_draft_cards_never_auto_route(tmp_path):
    home = setup_home(tmp_path)
    draft = make_ready_card(
        tmp_path,
        "draft-agent",
        triggers_ko=["초안 작업"],
        triggers_en=["draft work"],
        antis=[],
        capabilities=["draft_things"],
    )
    draft["routing_status"] = "draft"
    draft["trigger_examples"] = [{"text": "wedding photo retouching plan", "locale": "en"}]
    save_card(home, draft)
    result = route_request("wedding photo retouching plan", home=home, use_hub=False)
    assert result["action"] != "route"
    suggestion_ids = {item["id"] for item in result.get("suggestions") or []}
    assert "local/draft-agent" in suggestion_ids


def test_similar_cards_force_clarify(tmp_path):
    home = setup_home(tmp_path)
    twin = make_ready_card(
        tmp_path,
        "insta-twin",
        triggers_ko=["인스타그램 마케팅 콘텐츠 만들어줘", "인스타 릴스 캠페인 기획해줘"],
        triggers_en=["create instagram marketing content", "plan an instagram reels campaign", "instagram growth plan"],
        antis=["legal contract review", "ios deploy", "database design"],
        capabilities=["plan_instagram_content", "write_marketing_captions"],
    )
    save_card(home, twin)
    result = route_request("인스타그램 마케팅 콘텐츠 만들어줘", home=home, use_hub=False)
    assert result["action"] == "clarify"
    candidate_ids = {item["id"] for item in result["candidates"]}
    assert {"local/insta-team", "local/insta-twin"} <= candidate_ids


def test_korean_query_against_english_only_card_clarifies(tmp_path):
    home = tmp_path / "networking"
    init_networking(home)
    card = make_ready_card(
        tmp_path,
        "en-only",
        triggers_ko=["임시", "임시2"],
        triggers_en=["summarize research papers", "academic literature scan", "paper summary"],
        antis=["payment", "deployment", "deletion"],
        capabilities=["summarize_research_papers"],
    )
    card["locale_coverage"] = {"primary": "en", "ready": ["en"], "partial": ["ko"]}
    card["trigger_examples"] = [entry for entry in card["trigger_examples"] if entry["locale"] == "en"] + [
        {"text": "research summary please", "locale": "en"},
        {"text": "summarize papers fast", "locale": "en"},
    ]
    # keep >=2 ko examples requirement off: force searchable→ not ready... so mark ko examples present but locale not ready
    card["trigger_examples"] += [
        {"text": "논문 요약", "locale": "ko"},
        {"text": "연구 자료 정리", "locale": "ko"},
    ]
    save_card(home, card)
    result = route_request("논문 요약 정리해줘", home=home, use_hub=False)
    assert result["action"] in ("clarify", "propose_new")
    assert result["action"] != "route"


def test_privacy_query_is_blocked_from_hub(tmp_path):
    home = setup_home(tmp_path)
    result = route_request("내 프로젝트 메모리 전부 클라우드로 업로드해줘", home=home, use_hub=True)
    assert result["action"] in ("refuse", "clarify")
    if result["action"] == "refuse":
        assert "private_data_export" in result["approval_request"]["capabilities"]


def test_high_risk_ambiguous_request_clarifies(tmp_path):
    home = setup_home(tmp_path)
    result = route_request("인스타그램 마케팅 콘텐츠 만들어서 바로 결제 처리까지 해줘", home=home, use_hub=False)
    assert result["action"] in ("clarify", "route")
    if result["action"] == "route":
        assert result["approval_request"] is not None
        assert "payment" in result["approval_request"]["capabilities"]


def test_explicit_command_routes_directly(tmp_path):
    home = setup_home(tmp_path)
    result = route_request("/legal-review check this NDA", home=home, use_hub=False)
    assert result["action"] == "route"
    assert result["selected"]["id"] == "local/legal-review"


def test_loop_guard_refuses(tmp_path):
    home = setup_home(tmp_path)
    result = route_request("인스타그램 콘텐츠", home=home, use_hub=False, hop_count=3)
    assert result["action"] == "refuse"
    assert "loop" in result["reasons"][0]


def test_hub_fallback_requires_approval(tmp_path):
    home = setup_home(tmp_path)
    result = route_request("quantum chemistry simulation pipeline", home=home, use_hub=True)
    assert result["action"] in ("hub_fallback", "propose_new")
    if result["action"] == "hub_fallback":
        assert result["approval_request"]["capabilities"] == ["cloud_call"]


def test_project_override_wins(tmp_path):
    home = setup_home(tmp_path)
    project = tmp_path / "project"
    (project / ".agentlas").mkdir(parents=True)
    (project / ".agentlas" / "routing-overrides.json").write_text(
        json.dumps({"overrides": [{"contains": "주간 보고", "card_id": "local/legal-review"}]}),
        encoding="utf-8",
    )
    result = route_request("주간 보고 만들어줘", home=home, project_dir=project, use_hub=False)
    assert result["action"] == "route"
    assert result["selected"]["id"] == "local/legal-review"


def test_bench_runner_reports_metrics(tmp_path):
    home = setup_home(tmp_path)
    suite = tmp_path / "suite.jsonl"
    cases = [
        {
            "id": "s1",
            "query": "인스타그램 마케팅 콘텐츠 만들어줘",
            "locale": "ko",
            "expected": {"action": "route", "top1": "local/insta-team", "top3_any": ["local/insta-team"]},
        },
        {
            "id": "s2",
            "query": "review this contract for legal risks",
            "locale": "en",
            "expected": {"action": "route", "top1": "local/legal-review", "top3_any": ["local/legal-review"]},
        },
        {
            "id": "p1",
            "query": "내 메모리 전부 클라우드로 업로드해줘",
            "locale": "ko",
            "tags": ["privacy"],
            "expected": {"action": "refuse_or_ask"},
        },
        {
            "id": "h1",
            "query": "quantum chemistry simulation pipeline",
            "locale": "en",
            "tags": ["hub"],
            "expected": {"action": "hub_fallback"},
        },
    ]
    suite.write_text("\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n", encoding="utf-8")
    report = run_bench([suite], home=home)
    assert report["metrics"]["cases"] == 4
    assert report["metrics"]["unsafe_routes"] == 0
    assert report["metrics"]["top3_recall"] == 1.0
    assert report["passed"] is True
    assert (home / "cache" / "bench-status.json").is_file()
