import json

from agentlas_cloud.networking import init_networking, save_card
from agentlas_cloud.networking.gui_shortcut import open_local_gui_shortcut
from test_network_cards import make_ready_card


def test_explicit_local_gui_shortcut_opens_launcher(tmp_path):
    home = tmp_path / "networking"
    init_networking(home)
    package = tmp_path / "startup-package"
    (package / "scripts").mkdir(parents=True)
    launcher = package / "scripts" / "open.py"
    launcher.write_text(
        "import json\n"
        "print(json.dumps({'status': 'gui_ready', 'opened': False, 'gui_url': 'file:///tmp/demo.html'}))\n",
        encoding="utf-8",
    )
    card = make_ready_card(
        tmp_path,
        "startup-gui",
        triggers_ko=["스타트업 열어줘", "창업 gui"],
        triggers_en=["startup", "startup founder studio", "open startup gui"],
        antis=["legal", "payment", "deploy"],
        capabilities=["open_startup_gui"],
    )
    card["entrypoints"] = {
        "canonical_command": "/startup",
        "agent": "agents/00-startup-orchestrator/agent.md",
        "gui": "webapp/index.html",
        "gui_launcher": "scripts/open.py",
    }
    card["network_shortcut"] = {
        "enabled": True,
        "phrases": ["startup"],
        "mode": "local_gui",
    }
    card["source"] = {"kind": "local_path", "ref": str(package)}
    save_card(home, card)

    result = open_local_gui_shortcut("startup", home=home, no_open=True)

    assert result["action"] == "open_gui"
    assert result["status"] == "opened"
    assert result["selected"]["id"] == "local/startup-gui"
    assert result["launcher_result"]["status"] == "gui_ready"


def test_local_gui_shortcut_requires_exact_opt_in_phrase(tmp_path):
    home = tmp_path / "networking"
    init_networking(home)
    card = make_ready_card(
        tmp_path,
        "startup-gui",
        triggers_ko=["스타트업 열어줘", "창업 gui"],
        triggers_en=["startup", "startup founder studio", "open startup gui"],
        antis=["legal", "payment", "deploy"],
        capabilities=["open_startup_gui"],
    )
    card["network_shortcut"] = {
        "enabled": True,
        "phrases": ["startup"],
        "mode": "local_gui",
    }
    save_card(home, card)

    result = open_local_gui_shortcut("startup market research", home=home, no_open=True)

    assert result == {
        "action": "no_local_gui_shortcut",
        "status": "not_found",
        "query": "startup market research",
        "quarantined": 0,
    }
