"""Stormbreaker auto-runner for routed pipeline execution fabrics.

This module is the local product runner for `action: "pipeline"` route
decisions. The router still owns selection and policy labeling; the runner owns
packet materialization, optional external executor launch, packet ledgers, and
the final gate.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping

from .bootstrap import append_jsonl, atomic_write_json, networking_home, utc_now
from .execution_fabric import evaluate_final_gate
from .receipts import record_execution
from .router import route_request


RUNNER_VERSION = "stormbreaker.auto_runner.v1"


def run_stormbreaker_query(
    query: str,
    *,
    home: Path | str | None = None,
    project_dir: Path | str = ".",
    runtime: str | None = "terminal",
    use_hub: bool = True,
    hub_approved: bool = False,
    hub_only: bool = False,
    scope: str = "network",
    caller_id: str | None = None,
    session_inventory: list[Any] | None = None,
    executor_command: str | None = None,
    execute_card_commands: bool = False,
    max_workers: int | None = None,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Route a query, then run the returned Stormbreaker pipeline fabric."""

    decision = route_request(
        query,
        home=home,
        project_dir=project_dir,
        runtime=runtime,
        use_hub=use_hub,
        hub_approved=hub_approved,
        hub_only=hub_only,
        scope=scope,
        caller_id=caller_id,
        session_inventory=session_inventory,
    )
    result = run_stormbreaker_decision(
        decision,
        home=home,
        project_dir=project_dir,
        executor_command=executor_command,
        execute_card_commands=execute_card_commands,
        max_workers=max_workers,
        timeout_seconds=timeout_seconds,
    )
    result["route_decision"] = _decision_summary(decision)
    return result


def run_stormbreaker_decision(
    decision: Mapping[str, Any],
    *,
    home: Path | str | None = None,
    project_dir: Path | str = ".",
    executor_command: str | None = None,
    execute_card_commands: bool = False,
    max_workers: int | None = None,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Run a previously routed Stormbreaker pipeline decision."""

    if decision.get("action") != "pipeline":
        return {
            "status": "not_executed",
            "runner_version": RUNNER_VERSION,
            "reason": "Stormbreaker auto-runner only executes action=pipeline decisions",
            "route_action": decision.get("action"),
            "receipt_id": decision.get("receipt_id"),
        }

    fabric = decision.get("execution_fabric")
    if not isinstance(fabric, Mapping):
        return {
            "status": "error",
            "runner_version": RUNNER_VERSION,
            "reason": "pipeline decision is missing execution_fabric",
            "receipt_id": decision.get("receipt_id"),
        }

    project = Path(project_dir).expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    base = Path(home) if home else networking_home()
    pipeline_id = str(fabric.get("pipeline_id") or decision.get("pipeline_id") or uuid.uuid4().hex[:12])
    handoff_dir = str(decision.get("handoff_dir") or f".agentlas/pipeline/{pipeline_id}/")
    journal = _resolve_project_path(project, str(fabric.get("resume_policy", {}).get("journal") or f"{handoff_dir}stormbreaker-execution-ledger.jsonl"))
    journal.parent.mkdir(parents=True, exist_ok=True)

    mode = _execution_mode(executor_command, execute_card_commands)
    packet_by_id = {str(packet.get("packet_id")): dict(packet) for packet in fabric.get("packets") or [] if packet.get("packet_id")}
    packet_statuses: dict[str, str] = {}
    packet_results: list[dict[str, Any]] = []
    started_sessions: list[dict[str, Any]] = []
    max_parallel = _max_workers(max_workers, fabric)

    _append_journal(
        journal,
        {
            "event": "runner_started",
            "runner_version": RUNNER_VERSION,
            "pipeline_id": pipeline_id,
            "route_receipt_id": decision.get("receipt_id"),
            "execution_mode": mode,
            "max_workers": max_parallel,
        },
    )

    for group in fabric.get("parallel_groups") or []:
        group_id = str(group.get("group_id") or "group")
        group_packet_ids = [str(packet_id) for packet_id in group.get("packet_ids") or []]
        blocked_deps = [packet_id for packet_id in group.get("depends_on") or [] if packet_statuses.get(str(packet_id)) != "passing"]
        if blocked_deps:
            for packet_id in group_packet_ids:
                packet = packet_by_id.get(packet_id)
                if not packet:
                    continue
                result = _blocked_packet_result(
                    packet,
                    project=project,
                    journal=journal,
                    home=base,
                    parent_receipt_id=str(decision.get("receipt_id") or ""),
                    detail=f"dependency_not_passing: {', '.join(blocked_deps)}",
                    pipeline_id=pipeline_id,
                    group_id=group_id,
                )
                packet_statuses[packet_id] = result["status"]
                packet_results.append(result)
            continue

        ready_packets = [packet_by_id[packet_id] for packet_id in group_packet_ids if packet_id in packet_by_id]
        if not ready_packets:
            continue

        workers = min(max_parallel, len(ready_packets))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="stormbreaker-packet") as executor:
            futures = {
                executor.submit(
                    _run_packet,
                    packet,
                    project=project,
                    home=base,
                    journal=journal,
                    parent_receipt_id=str(decision.get("receipt_id") or ""),
                    pipeline_id=pipeline_id,
                    group_id=group_id,
                    executor_command=executor_command,
                    execute_card_commands=execute_card_commands,
                    timeout_seconds=timeout_seconds,
                ): packet
                for packet in ready_packets
            }
            for future in as_completed(futures):
                packet = futures[future]
                packet_id = str(packet["packet_id"])
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - defensive finalizer
                    result = _blocked_packet_result(
                        packet,
                        project=project,
                        journal=journal,
                        home=base,
                        parent_receipt_id=str(decision.get("receipt_id") or ""),
                        detail=f"runner_exception: {exc}",
                        pipeline_id=pipeline_id,
                        group_id=group_id,
                    )
                packet_statuses[packet_id] = result["status"]
                packet_results.append(result)
                started_sessions.append(
                    {
                        "packet_id": packet_id,
                        "session_id": result.get("session_id"),
                        "status": result["status"],
                        "mode": result.get("execution_mode"),
                    }
                )

    final_gate = evaluate_final_gate(dict(fabric), packet_statuses)
    status = "completed" if final_gate["can_report_success"] else "blocked"
    _append_journal(
        journal,
        {
            "event": "runner_finished",
            "pipeline_id": pipeline_id,
            "status": status,
            "final_gate": final_gate,
        },
    )

    return {
        "status": status,
        "runner_version": RUNNER_VERSION,
        "execution_mode": mode,
        "claim_level": _claim_level(mode),
        "pipeline_id": pipeline_id,
        "route_receipt_id": decision.get("receipt_id"),
        "handoff_dir": handoff_dir,
        "journal": _relative_to_project(project, journal),
        "max_workers": max_parallel,
        "sessions_started": started_sessions,
        "packet_statuses": packet_statuses,
        "packets": sorted(packet_results, key=lambda item: (item.get("stage_order") or 0, item.get("packet_id") or "")),
        "final_gate": final_gate,
    }


def _run_packet(
    packet: dict[str, Any],
    *,
    project: Path,
    home: Path,
    journal: Path,
    parent_receipt_id: str,
    pipeline_id: str,
    group_id: str,
    executor_command: str | None,
    execute_card_commands: bool,
    timeout_seconds: int,
) -> dict[str, Any]:
    packet_id = str(packet["packet_id"])
    write_scope = _resolve_project_path(project, str(packet.get("write_scope") or f".agentlas/pipeline/{pipeline_id}/{packet_id}/"))
    write_scope.mkdir(parents=True, exist_ok=True)
    packet_file = write_scope / "packet.json"
    stdout_file = write_scope / "stdout.log"
    stderr_file = write_scope / "stderr.log"
    result_file = write_scope / "packet-result.json"
    session = packet.get("session_hint") or {}
    session_id = str(session.get("session_id") or "host:primary")
    mode = _execution_mode(executor_command, execute_card_commands)
    started_at = utc_now()
    execution_receipt_id = uuid.uuid4().hex[:16]

    packet_contract = {
        "runner_version": RUNNER_VERSION,
        "packet": packet,
        "pipeline_id": pipeline_id,
        "parallel_group": group_id,
        "session_hint": session,
        "write_scope": str(write_scope),
        "data_policy": packet.get("data_policy") or [],
    }
    atomic_write_json(packet_file, packet_contract)
    _append_journal(
        journal,
        {
            "event": "packet_started",
            "pipeline_id": pipeline_id,
            "packet_id": packet_id,
            "stage": packet.get("stage"),
            "session_id": session_id,
            "parallel_group": group_id,
            "write_scope": _relative_to_project(project, write_scope),
            "execution_mode": mode,
        },
    )

    completed = _execute_packet_command(
        packet,
        project=project,
        write_scope=write_scope,
        packet_file=packet_file,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
        executor_command=executor_command,
        execute_card_commands=execute_card_commands,
        timeout_seconds=timeout_seconds,
    )
    status = "passing" if completed["ok"] else "blocked"
    detail = str(completed["detail"])
    result = {
        "runner_version": RUNNER_VERSION,
        "execution_receipt_id": execution_receipt_id,
        "packet_id": packet_id,
        "pipeline_id": pipeline_id,
        "stage": packet.get("stage"),
        "stage_order": packet.get("stage_order"),
        "card": packet.get("card"),
        "session_id": session_id,
        "parallel_group": group_id,
        "execution_mode": mode,
        "status": status,
        "detail": detail,
        "started_at": started_at,
        "finished_at": utc_now(),
        "write_scope": _relative_to_project(project, write_scope),
        "packet_file": _relative_to_project(project, packet_file),
        "result_file": _relative_to_project(project, result_file),
        "stdout_file": _relative_to_project(project, stdout_file),
        "stderr_file": _relative_to_project(project, stderr_file),
        "returncode": completed.get("returncode"),
    }
    atomic_write_json(result_file, result)
    record_execution(
        execution_receipt_id,
        str(packet.get("card") or "unknown"),
        status,
        home=home,
        detail=detail,
        pipeline_id=pipeline_id,
        packet_id=packet_id,
        stage_order=_int_or_none(packet.get("stage_order")),
        session_id=session_id,
        parallel_group=group_id,
        parent_receipt_id=parent_receipt_id or None,
    )
    _append_journal(journal, {"event": "packet_finished", **result})
    return result


def _execute_packet_command(
    packet: Mapping[str, Any],
    *,
    project: Path,
    write_scope: Path,
    packet_file: Path,
    stdout_file: Path,
    stderr_file: Path,
    executor_command: str | None,
    execute_card_commands: bool,
    timeout_seconds: int,
) -> dict[str, Any]:
    if executor_command:
        return _run_subprocess(
            executor_command,
            packet,
            project=project,
            write_scope=write_scope,
            packet_file=packet_file,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            timeout_seconds=timeout_seconds,
        )

    if execute_card_commands:
        command = str(packet.get("canonical_command") or "").strip()
        if not command:
            stdout_file.write_text("", encoding="utf-8")
            stderr_file.write_text("card has no canonical_command\n", encoding="utf-8")
            return {"ok": False, "detail": "missing canonical_command", "returncode": None}
        if command.startswith("/"):
            stdout_file.write_text("", encoding="utf-8")
            stderr_file.write_text(
                f"{command} is a runtime slash command, not a shell command. Use --executor-command to bridge this runtime.\n",
                encoding="utf-8",
            )
            return {"ok": False, "detail": "slash_command_requires_runtime_adapter", "returncode": None}
        return _run_subprocess(
            command,
            packet,
            project=project,
            write_scope=write_scope,
            packet_file=packet_file,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            timeout_seconds=timeout_seconds,
        )

    stdout_file.write_text("packet contract materialized; no external executor configured\n", encoding="utf-8")
    stderr_file.write_text("", encoding="utf-8")
    return {"ok": True, "detail": "packet_contract_materialized", "returncode": 0}


def _run_subprocess(
    command: str,
    packet: Mapping[str, Any],
    *,
    project: Path,
    write_scope: Path,
    packet_file: Path,
    stdout_file: Path,
    stderr_file: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    env = os.environ.copy()
    env.update(
        {
            "STORMBREAKER_PACKET_ID": str(packet.get("packet_id") or ""),
            "STORMBREAKER_STAGE": str(packet.get("stage") or ""),
            "STORMBREAKER_STAGE_ORDER": str(packet.get("stage_order") or ""),
            "STORMBREAKER_CARD_ID": str(packet.get("card") or ""),
            "STORMBREAKER_CANONICAL_COMMAND": str(packet.get("canonical_command") or ""),
            "STORMBREAKER_WRITE_SCOPE": str(write_scope),
            "STORMBREAKER_PACKET_FILE": str(packet_file),
            "STORMBREAKER_PROJECT_DIR": str(project),
        }
    )
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(project),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_file.write_text(exc.stdout or "", encoding="utf-8")
        stderr_file.write_text((exc.stderr or "") + f"\ncommand timed out after {timeout_seconds}s\n", encoding="utf-8")
        return {"ok": False, "detail": f"executor_timeout:{timeout_seconds}s", "returncode": None}
    except OSError as exc:
        stdout_file.write_text("", encoding="utf-8")
        stderr_file.write_text(str(exc), encoding="utf-8")
        return {"ok": False, "detail": f"executor_os_error:{exc}", "returncode": None}

    stdout_file.write_text(completed.stdout or "", encoding="utf-8")
    stderr_file.write_text(completed.stderr or "", encoding="utf-8")
    if completed.returncode == 0:
        return {"ok": True, "detail": "executor_completed", "returncode": completed.returncode}
    return {"ok": False, "detail": f"executor_failed:{completed.returncode}", "returncode": completed.returncode}


def _blocked_packet_result(
    packet: Mapping[str, Any],
    *,
    project: Path,
    journal: Path,
    home: Path,
    parent_receipt_id: str,
    detail: str,
    pipeline_id: str,
    group_id: str,
) -> dict[str, Any]:
    packet_id = str(packet["packet_id"])
    write_scope = _resolve_project_path(project, str(packet.get("write_scope") or f".agentlas/pipeline/{pipeline_id}/{packet_id}/"))
    write_scope.mkdir(parents=True, exist_ok=True)
    execution_receipt_id = uuid.uuid4().hex[:16]
    result = {
        "runner_version": RUNNER_VERSION,
        "execution_receipt_id": execution_receipt_id,
        "packet_id": packet_id,
        "pipeline_id": pipeline_id,
        "stage": packet.get("stage"),
        "stage_order": packet.get("stage_order"),
        "card": packet.get("card"),
        "session_id": (packet.get("session_hint") or {}).get("session_id") or "host:primary",
        "parallel_group": group_id,
        "execution_mode": "dependency_gate",
        "status": "blocked",
        "detail": detail,
        "started_at": utc_now(),
        "finished_at": utc_now(),
        "write_scope": _relative_to_project(project, write_scope),
        "packet_file": _relative_to_project(project, write_scope / "packet.json"),
        "result_file": _relative_to_project(project, write_scope / "packet-result.json"),
    }
    atomic_write_json(write_scope / "packet.json", {"runner_version": RUNNER_VERSION, "packet": packet, "blocked_by": detail})
    atomic_write_json(write_scope / "packet-result.json", result)
    record_execution(
        execution_receipt_id,
        str(packet.get("card") or "unknown"),
        "blocked",
        home=home,
        detail=detail,
        pipeline_id=pipeline_id,
        packet_id=packet_id,
        stage_order=_int_or_none(packet.get("stage_order")),
        session_id=str(result["session_id"]),
        parallel_group=group_id,
        parent_receipt_id=parent_receipt_id or None,
    )
    _append_journal(journal, {"event": "packet_finished", **result})
    return result


def _append_journal(path: Path, payload: dict[str, Any]) -> None:
    append_jsonl(path, {"ts": utc_now(), **payload})


def _resolve_project_path(project: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = project / path
    resolved = path.resolve()
    try:
        resolved.relative_to(project)
    except ValueError as exc:
        raise ValueError(f"Stormbreaker write path escapes project: {raw_path}") from exc
    return resolved


def _relative_to_project(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project))
    except ValueError:
        return str(path)


def _execution_mode(executor_command: str | None, execute_card_commands: bool) -> str:
    if executor_command:
        return "executor_command"
    if execute_card_commands:
        return "card_command"
    return "materialize"


def _claim_level(mode: str) -> str:
    if mode == "materialize":
        return "handoff_artifacts_materialized"
    if mode == "card_command":
        return "card_command_executed"
    return "external_executor_completed"


def _max_workers(configured: int | None, fabric: Mapping[str, Any]) -> int:
    if configured is not None:
        return max(1, int(configured))
    sessions = fabric.get("sessions") or []
    total = 0
    for session in sessions:
        if not isinstance(session, Mapping):
            continue
        try:
            total += int(session.get("max_parallel") or 1)
        except (TypeError, ValueError):
            total += 1
    return max(1, total or 1)


def _decision_summary(decision: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "action": decision.get("action"),
        "receipt_id": decision.get("receipt_id"),
        "match_reason": decision.get("match_reason"),
        "allowed_by": decision.get("allowed_by") or [],
        "blocked_by_axiom": decision.get("blocked_by_axiom") or [],
    }


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
