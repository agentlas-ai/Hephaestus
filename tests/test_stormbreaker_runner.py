import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

from agentlas_cloud.cli import main
from agentlas_cloud.networking import run_stormbreaker_query
from test_network_pipeline import pipeline_home


def executor_script(tmp_path, body: str) -> str:
    script = tmp_path / "executor.py"
    script.write_text(body, encoding="utf-8")
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"


def test_stormbreaker_runner_completes_pipeline_packets(tmp_path):
    home = pipeline_home(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    executor = executor_script(
        tmp_path,
        """
import os
from pathlib import Path

scope = Path(os.environ["STORMBREAKER_WRITE_SCOPE"])
scope.mkdir(parents=True, exist_ok=True)
(scope / "executor-artifact.txt").write_text(
    os.environ["STORMBREAKER_PACKET_ID"] + "\\n" + os.environ["STORMBREAKER_STAGE"],
    encoding="utf-8",
)
""",
    )

    result = run_stormbreaker_query(
        "웹앱 기획부터 구현, 테스트 검증까지 끝까지 해줘",
        home=home,
        project_dir=project,
        use_hub=False,
        session_inventory=[
            {"session_id": "claude:planner", "provider": "claude", "capabilities": ["planning"]},
            {"session_id": "codex:builder", "provider": "codex", "capabilities": ["coding"]},
            {"session_id": "deepseek:verifier", "provider": "deepseek", "capabilities": ["verification"]},
        ],
        executor_command=executor,
    )

    assert result["status"] == "completed"
    assert result["execution_mode"] == "executor_command"
    assert result["final_gate"]["can_report_success"] is True
    assert all(status == "passing" for status in result["packet_statuses"].values())
    assert len(result["packets"]) == 3
    assert (project / result["journal"]).is_file()
    assert all((project / packet["write_scope"] / "executor-artifact.txt").is_file() for packet in result["packets"])
    ledger = (home / "ledgers" / "executions.jsonl").read_text(encoding="utf-8")
    assert '"parent_receipt_id"' in ledger
    assert '"session_id": "codex:builder"' in ledger


def test_stormbreaker_runner_blocks_dependents_after_failed_packet(tmp_path):
    home = pipeline_home(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    executor = executor_script(
        tmp_path,
        """
import os
import sys

if os.environ["STORMBREAKER_STAGE"] == "build":
    sys.exit(7)
""",
    )

    result = run_stormbreaker_query(
        "웹앱 기획부터 구현, 테스트 검증까지 끝까지 해줘",
        home=home,
        project_dir=project,
        use_hub=False,
        executor_command=executor,
    )

    assert result["status"] == "blocked"
    assert result["final_gate"]["can_report_success"] is False
    build_packet = next(packet for packet in result["packets"] if packet["stage"] == "build")
    verify_packet = next(packet for packet in result["packets"] if packet["stage"] == "verify")
    assert build_packet["status"] == "blocked"
    assert build_packet["detail"] == "executor_failed:7"
    assert verify_packet["status"] == "blocked"
    assert verify_packet["detail"].startswith("dependency_not_passing:")


def test_stormbreaker_cli_runs_pipeline(tmp_path, monkeypatch, capsys):
    home = pipeline_home(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("AGENTLAS_NETWORKING_HOME", str(home))
    executor = executor_script(tmp_path, "import os\nprint(os.environ['STORMBREAKER_PACKET_ID'])\n")

    code = main(
        [
            "stormbreaker",
            "run",
            "웹앱 기획부터 구현, 테스트 검증까지 끝까지 해줘",
            "--project",
            str(project),
            "--no-hub",
            "--executor-command",
            executor,
            "--session-inventory",
            json.dumps([{"session_id": "codex:local", "capabilities": ["planning", "coding", "verification"], "local": True}]),
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "completed"
    assert payload["route_decision"]["action"] == "pipeline"
    assert payload["claim_level"] == "external_executor_completed"


def test_stormbreaker_cli_background_run_writes_result(tmp_path, monkeypatch, capsys):
    home = pipeline_home(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("AGENTLAS_NETWORKING_HOME", str(home))
    executor = executor_script(tmp_path, "import os\nprint(os.environ['STORMBREAKER_PACKET_ID'])\n")

    code = main(
        [
            "stormbreaker",
            "run",
            "웹앱 기획부터 구현, 테스트 검증까지 끝까지 해줘",
            "--project",
            str(project),
            "--no-hub",
            "--executor-command",
            executor,
            "--background",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "background_started"
    result_file = Path(payload["result_file"])
    for _ in range(50):
        if result_file.is_file():
            break
        time.sleep(0.1)
    assert result_file.is_file()
    result = json.loads(result_file.read_text(encoding="utf-8"))
    assert result["status"] == "completed"
    assert result["final_gate"]["can_report_success"] is True


def test_hephaestus_storm_terminal_command_runs_pipeline(tmp_path):
    home = pipeline_home(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    executor = executor_script(tmp_path, "import os\nprint(os.environ['STORMBREAKER_PACKET_ID'])\n")
    env = dict(**os.environ, AGENTLAS_NETWORKING_HOME=str(home))

    completed = subprocess.run(
        [
            "bin/hephaestus-storm",
            "웹앱 기획부터 구현, 테스트 검증까지 끝까지 해줘",
            "--project",
            str(project),
            "--no-hub",
            "--executor-command",
            executor,
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "completed"
    assert payload["route_decision"]["action"] == "pipeline"


def test_route_auto_run_background_starts_for_pipeline(tmp_path, monkeypatch, capsys):
    home = pipeline_home(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("AGENTLAS_NETWORKING_HOME", str(home))
    executor = executor_script(tmp_path, "import os\nprint(os.environ['STORMBREAKER_PACKET_ID'])\n")

    code = main(
        [
            "route",
            "웹앱 기획부터 구현, 테스트 검증까지 끝까지 해줘",
            "--project",
            str(project),
            "--no-hub",
            "--auto-run",
            "--background",
            "--executor-command",
            executor,
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "background_started"
    assert payload["route_receipt_id"]
    assert payload["decision_file"]
    result_file = Path(payload["result_file"])
    for _ in range(50):
        if result_file.is_file():
            break
        time.sleep(0.1)
    assert result_file.is_file()
    result = json.loads(result_file.read_text(encoding="utf-8"))
    assert result["status"] == "completed"


def test_route_auto_run_skips_non_pipeline_decision(tmp_path, monkeypatch, capsys):
    home = pipeline_home(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("AGENTLAS_NETWORKING_HOME", str(home))

    code = main(
        [
            "route",
            "웹앱 구현해줘",
            "--project",
            str(project),
            "--no-hub",
            "--auto-run",
            "--background",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] != "pipeline"
    assert payload["auto_run"]["status"] == "skipped"
