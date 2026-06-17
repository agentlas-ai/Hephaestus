"""Pipeline routing (a Hephaestus Network 2.0 feature, not a new version).

Chains multiple teams into one deliverable — e.g. PRD team → dev HQ → QA —
via the produces/consumes artifact contracts on routing cards. The planner is
deterministic (no LLM) and returns a PLAN only; the calling runtime executes
stages one by one with its own execution permissions and records artifacts under
<project>/.agentlas/pipeline/<pipeline_id>/.

Over-decomposition guard: a pipeline is only planned when the request is
plan-anchored (a planning intent plus at least one more stage intent) or uses
an explicit end-to-end phrase. Single-intent requests never get decomposed.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

from pathlib import Path

# Canonical stage order. Each stage: (key, intent keywords, artifact kind).
STAGE_DEFS: list[tuple[str, set[str], str]] = [
    (
        "plan",
        {"기획", "요구사항", "요건", "스펙", "prd", "spec", "requirements", "product plan"},
        "prd",
    ),
    (
        "build",
        {"구현", "개발", "제작", "빌드", "코딩", "웹앱", "사이트", "build", "implement", "develop", "code it", "app", "website"},
        "codebase_change",
    ),
    (
        "verify",
        {"검증", "테스트", "점검", "검수", "qa", "test", "verify", "validate"},
        "qa_report",
    ),
]

EXPLICIT_PIPELINE_PHRASES = {
    "끝까지", "전 과정", "한 번에 끝", "원스톱", "파이프라인으로",
    "end to end", "end-to-end", "from prd to", "all the way to",
}


def detect_stages(query: str) -> list[tuple[str, str]]:
    """Return [(stage_key, artifact_kind)] in canonical order for the query."""
    lowered = (query or "").lower()
    hits = [(key, kind) for key, keywords, kind in STAGE_DEFS if any(word in lowered for word in keywords)]
    explicit = any(phrase in lowered for phrase in EXPLICIT_PIPELINE_PHRASES)
    if len(hits) < 2:
        return []
    # Plan-anchored or explicitly end-to-end — otherwise it is a single task
    # that merely mentions testing/building vocabulary.
    if hits[0][0] != "plan" and not explicit:
        return []
    return hits


def _producers(cards: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    found = []
    for card in cards:
        for produced in card.get("produces") or []:
            if isinstance(produced, dict) and produced.get("kind") == kind:
                found.append(card)
                break
    return found


def _consumes_kind(card: dict[str, Any], kind: str) -> bool:
    return any(
        isinstance(entry, dict) and entry.get("kind") == kind
        for entry in card.get("consumes") or []
    )


def plan_pipeline(
    query: str,
    usable_cards: list[dict[str, Any]],
    score_of: Callable[[dict[str, Any]], float],
    max_stages: int = 3,
    project_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    """Build a deterministic stage plan, or None when no valid chain exists."""
    _graph_enabled = project_dir is not None
    stages_wanted = detect_stages(query)[:max_stages]
    if len(stages_wanted) < 2:
        return None

    chosen: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    previous_kind: str | None = None
    for stage_key, kind in stages_wanted:
        producers = [card for card in _producers(usable_cards, kind) if str(card.get("id")) not in used_ids]
        if not producers:
            continue
        # Rank: consumes the previous artifact first, then query score, then id
        # for determinism.
        producers.sort(
            key=lambda card: (
                -(1 if previous_kind and _consumes_kind(card, previous_kind) else 0),
                -score_of(card),
                str(card.get("id")),
            )
        )
        card = producers[0]
        used_ids.add(str(card.get("id")))
        chosen.append(
            {
                "order": len(chosen) + 1,
                "stage": stage_key,
                "card": card.get("id"),
                "name": card.get("name"),
                "canonical_command": (card.get("entrypoints") or {}).get("canonical_command"),
                "consumes": [previous_kind] if previous_kind and _consumes_kind(card, previous_kind) else [],
                "produces": [kind],
            }
        )
        previous_kind = kind

    if len(chosen) < 2:
        return None
    graph_path: list[dict[str, str]] = []
    for idx, stage in enumerate(chosen):
        card_id = str(stage["card"])
        produced = str(stage["produces"][0])
        produced_id = f"artifact:{produced}" if not produced.startswith("artifact:") else produced
        if stage.get("consumes"):
            previous = str(stage["consumes"][0])
            previous_id = f"artifact:{previous}" if not previous.startswith("artifact:") else previous
            graph_path.append({"from": card_id, "to": previous_id, "relation": "consumes"})
        graph_path.append({"from": card_id, "to": produced_id, "relation": "produces"})

    pipeline_id = uuid.uuid4().hex[:12]
    if not _graph_enabled:
        # preserve historical shape while still exposing stage-level intent traces
        # as a logical graph for downstream audit tooling.
        exposed_path = []
    else:
        exposed_path = graph_path

    return {
        "pipeline_id": pipeline_id,
        "stages": chosen,
        "handoff_dir": f".agentlas/pipeline/{pipeline_id}/",
        "graph_path": exposed_path,
        "match_reason": "pipeline_graph_sequence" if _graph_enabled else "pipeline_legacy_sequence",
        "allowed_by": ["local_keyword_match"] if chosen else [],
        "blocked_by_axiom": [],
        "runner_contract": [
            "execute stages in order using the host runtime's safety and permission model",
            "record each stage's artifacts under handoff_dir/<order>-<kind>/ and pass paths to the next stage",
            "on failure: stop, report progress and the remaining plan — never retry silently",
        ],
    }
