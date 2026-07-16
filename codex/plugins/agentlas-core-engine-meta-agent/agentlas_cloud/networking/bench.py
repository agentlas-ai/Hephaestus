"""Routing benchmark runner.

Measures: top-1 accuracy, top-3 recall, clarify rate, unsafe route rate,
wrong plugin attachment rate, latency p50/p95, hub fallback correctness, and
ko/en coverage. Routing quality is a testable product requirement — the
result is persisted to cache/bench-status.json and gates auto routing.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .bootstrap import atomic_write_json, networking_home, utc_now
from .router import route_request

DEFAULT_CRITERIA = {"min_top3_recall": 0.9, "max_unsafe": 0, "min_hub_correct": 0.9}


def _load_suite_rows(path: Path) -> list[tuple[int, dict[str, Any]]]:
    cases: list[tuple[int, dict[str, Any]]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            case = json.loads(line)
        except ValueError:
            continue
        if isinstance(case, dict) and case.get("query"):
            cases.append((line_number, case))
    return cases


def load_suite(path: Path) -> list[dict[str, Any]]:
    return [case for _, case in _load_suite_rows(path)]


def _case_identity(case: dict[str, Any]) -> str:
    raw_identity = case.get("id")
    if raw_identity is not None:
        identity = str(raw_identity).strip()
        if identity:
            return identity
    canonical = json.dumps(case, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"anonymous:{digest}"


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_benchmark_state(report: Any) -> dict[str, Any]:
    """Validate the persisted fields that make a benchmark receipt routable."""

    blockers: list[dict[str, Any]] = []
    if not isinstance(report, dict):
        return {
            "ready": False,
            "blockers": [
                {
                    "code": "benchmark_not_run",
                    "message": "benchmark receipt is missing or unreadable",
                }
            ],
        }

    suites = report.get("suites")
    if not isinstance(suites, list) or not any(isinstance(item, str) and item.strip() for item in suites):
        blockers.append({"code": "no_suites", "message": "benchmark has no loaded suites"})

    metrics = report.get("metrics")
    case_count = metrics.get("cases") if isinstance(metrics, dict) else None
    if not _is_count(case_count) or case_count == 0:
        blockers.append({"code": "no_cases", "message": "benchmark has zero runnable cases"})

    diagnostics = report.get("diagnostics")
    if not isinstance(diagnostics, dict):
        blockers.append(
            {
                "code": "identity_diagnostics_missing",
                "message": "benchmark receipt has no case-identity diagnostics; rerun the benchmark",
            }
        )
        return {"ready": False, "blockers": blockers}

    case_rows = diagnostics.get("case_rows")
    unique_cases = diagnostics.get("unique_cases")
    duplicate_cases = diagnostics.get("duplicate_case_identities")
    metrics_unique_cases = metrics.get("unique_cases") if isinstance(metrics, dict) else None
    if not _is_count(case_rows) or not _is_count(unique_cases) or not isinstance(duplicate_cases, list):
        blockers.append(
            {
                "code": "identity_diagnostics_invalid",
                "message": "benchmark case-identity diagnostics are malformed",
            }
        )
        return {"ready": False, "blockers": blockers}

    if _is_count(case_count) and case_rows != case_count:
        blockers.append(
            {
                "code": "case_count_mismatch",
                "message": "benchmark metrics and identity diagnostics disagree on case rows",
                "metrics_cases": case_count,
                "diagnostic_case_rows": case_rows,
            }
        )
    if not _is_count(metrics_unique_cases) or metrics_unique_cases != unique_cases:
        blockers.append(
            {
                "code": "unique_case_count_mismatch",
                "message": "benchmark metrics and identity diagnostics disagree on unique cases",
                "metrics_unique_cases": metrics_unique_cases,
                "diagnostic_unique_cases": unique_cases,
            }
        )
    if unique_cases > case_rows or (not duplicate_cases and unique_cases != case_rows):
        blockers.append(
            {
                "code": "identity_count_invalid",
                "message": "benchmark unique-case counts are inconsistent with duplicate diagnostics",
                "case_rows": case_rows,
                "unique_cases": unique_cases,
            }
        )
    if duplicate_cases:
        identities = sorted(
            str(item.get("identity"))
            for item in duplicate_cases
            if isinstance(item, dict) and item.get("identity") is not None
        )
        blockers.append(
            {
                "code": "duplicate_case_identities",
                "message": f"benchmark contains {len(duplicate_cases)} duplicate case identities",
                "count": len(duplicate_cases),
                "identities": identities,
            }
        )

    return {"ready": not blockers, "blockers": blockers}


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(pct * (len(ordered) - 1))))
    return ordered[index]


def _candidate_ids(result: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    selected = result.get("selected") or {}
    if selected.get("id"):
        ids.append(str(selected["id"]))
    for candidate in result.get("candidates") or []:
        cid = str(candidate.get("id"))
        if cid not in ids:
            ids.append(cid)
    for suggestion in result.get("suggestions") or []:
        sid = str(suggestion.get("id"))
        if sid not in ids:
            ids.append(sid)
    return ids


def run_bench(
    suites: list[Path | str],
    home: Path | str | None = None,
    criteria: dict[str, Any] | None = None,
    write_status: bool = True,
) -> dict[str, Any]:
    base = Path(home) if home else networking_home()
    rules = {**DEFAULT_CRITERIA, **(criteria or {})}
    cases: list[dict[str, Any]] = []
    suite_names: list[str] = []
    identity_occurrences: dict[str, list[dict[str, Any]]] = {}
    for suite in suites:
        suite_path = Path(suite)
        if suite_path.is_file():
            suite_name = suite_path.stem
            suite_names.append(suite_name)
            for line_number, case in _load_suite_rows(suite_path):
                cases.append(case)
                identity = _case_identity(case)
                identity_occurrences.setdefault(identity, []).append(
                    {"suite": suite_name, "line": line_number}
                )

    total = len(cases)
    duplicate_case_identities = [
        {
            "identity": identity,
            "occurrences": sorted(
                occurrences,
                key=lambda item: (str(item["suite"]), int(item["line"])),
            ),
        }
        for identity, occurrences in sorted(identity_occurrences.items())
        if len(occurrences) > 1
    ]
    latencies: list[float] = []
    top1_hits = top1_total = 0
    top3_hits = top3_total = 0
    action_hits = action_total = 0
    clarifies = 0
    unsafe = 0
    privacy_total = 0
    plugin_total = plugin_wrong = 0
    hub_total = hub_correct = 0
    pipeline_total = pipeline_ok = 0
    locale_stats: dict[str, dict[str, int]] = {}
    failures: list[dict[str, Any]] = []

    for case in cases:
        expected = case.get("expected") or {}
        tags = set(case.get("tags") or [])
        started = time.perf_counter()
        result = route_request(str(case["query"]), home=base, use_hub=False)
        latencies.append((time.perf_counter() - started) * 1000.0)
        action = str(result.get("action"))
        candidate_ids = _candidate_ids(result)
        locale = str(case.get("locale") or result.get("locale") or "en")
        stats = locale_stats.setdefault(locale, {"total": 0, "ok": 0})
        stats["total"] += 1
        case_ok = True

        if action == "clarify":
            clarifies += 1

        expected_action = expected.get("action")
        if expected_action:
            action_total += 1
            allowed = {expected_action}
            if expected_action == "refuse_or_ask":
                allowed = {"refuse", "clarify"}
            if expected_action == "hub_fallback":
                allowed = {"hub_fallback", "propose_new", "hub_candidates"}
            if action in allowed:
                action_hits += 1
            else:
                case_ok = False
            if "hub" in tags:
                hub_total += 1
                if action in allowed:
                    hub_correct += 1

        if expected.get("stage_kinds") is not None:
            pipeline_total += 1
            got_kinds = [
                (stage.get("produces") or [None])[0]
                for stage in (result.get("stages") or [])
            ]
            if got_kinds == list(expected["stage_kinds"]):
                pipeline_ok += 1
            else:
                case_ok = False

        if expected.get("top1"):
            top1_total += 1
            if candidate_ids[:1] == [str(expected["top1"])]:
                top1_hits += 1
            else:
                case_ok = False

        if expected.get("top3_any"):
            top3_total += 1
            wanted = {str(item) for item in expected["top3_any"]}
            if wanted & set(candidate_ids[:3]):
                top3_hits += 1
            else:
                case_ok = False

        if "privacy" in tags:
            privacy_total += 1
            # The router is not the executor and no longer emits safety gates.
            # Privacy benchmark safety means no local runnable target was selected.
            is_safe = result.get("selected") is None
            if not is_safe:
                unsafe += 1
                case_ok = False

        if expected.get("plugin"):
            plugin_total += 1
            selected = result.get("selected") or {}
            plugin_ids = {str((plugin or {}).get("id")) for plugin in selected.get("required_plugins") or []}
            if str(expected["plugin"]) not in plugin_ids:
                plugin_wrong += 1
                case_ok = False

        if case_ok:
            stats["ok"] += 1
        else:
            failures.append(
                {
                    "id": case.get("id"),
                    "query": case.get("query"),
                    "expected": expected,
                    "got": {"action": action, "top": candidate_ids[:3]},
                }
            )

    metrics = {
        "cases": total,
        "unique_cases": len(identity_occurrences),
        "top1_accuracy": round(top1_hits / top1_total, 4) if top1_total else None,
        "top3_recall": round(top3_hits / top3_total, 4) if top3_total else None,
        "action_accuracy": round(action_hits / action_total, 4) if action_total else None,
        "clarify_rate": round(clarifies / total, 4) if total else 0.0,
        "unsafe_route_rate": round(unsafe / privacy_total, 4) if privacy_total else 0.0,
        "unsafe_routes": unsafe,
        "wrong_plugin_rate": round(plugin_wrong / plugin_total, 4) if plugin_total else None,
        "hub_fallback_correct": round(hub_correct / hub_total, 4) if hub_total else None,
        "pipeline_plan_accuracy": round(pipeline_ok / pipeline_total, 4) if pipeline_total else None,
        "latency_ms_p50": round(_percentile(latencies, 0.50), 2),
        "latency_ms_p95": round(_percentile(latencies, 0.95), 2),
        "locale_breakdown": {
            locale: {"total": stats["total"], "ok": stats["ok"], "rate": round(stats["ok"] / stats["total"], 4)}
            for locale, stats in locale_stats.items()
            if stats["total"]
        },
    }

    quality_passed = True
    if metrics["top3_recall"] is not None and metrics["top3_recall"] < float(rules["min_top3_recall"]):
        quality_passed = False
    if unsafe > int(rules["max_unsafe"]):
        quality_passed = False
    if metrics["hub_fallback_correct"] is not None and metrics["hub_fallback_correct"] < float(rules["min_hub_correct"]):
        quality_passed = False

    report = {
        "ts": utc_now(),
        "suites": suite_names,
        "passed": False,
        "criteria": rules,
        "metrics": metrics,
        "diagnostics": {
            "case_rows": total,
            "unique_cases": len(identity_occurrences),
            "duplicate_case_identities": duplicate_case_identities,
        },
        "failures": failures[:25],
    }
    report["readiness"] = validate_benchmark_state(report)
    report["passed"] = bool(quality_passed and report["readiness"]["ready"])
    if write_status:
        atomic_write_json(base / "cache" / "bench-status.json", report)
    return report
