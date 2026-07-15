"""Shared helpers for Agent Workforce Ontology public contracts."""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping


ID_SAFE_RE = re.compile(r"[^a-z0-9._:/@-]+")
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._:/@+-]*|[가-힣]{2,}", re.IGNORECASE)
WORKFORCE_ONTOLOGY_VERSION = "awo:2026-07-15.2"
WORKFORCE_ONTOLOGY_SNAPSHOT_SHA256 = "d6d30d45fe8d35fb785e165d1e80c6471a72436f0160c3933c21d4a31bf2fb32"

# Exact finite aggregate codes emitted by the Hub workforce search boundary.
# These codes describe eligibility classes only. They must never embed a
# candidate/release identity, raw profile content, history, or a free-form
# reason supplied by an agent.
WORKFORCE_COVERAGE_GAP_CODES = (
    "gap:minimum-candidate-count",
    "gap:no-hard-eligible-candidate",
    "gap:excluded:forbidden-community",
    "gap:excluded:release-not-active",
    "gap:excluded:structural-or-security-invalid",
    "gap:excluded:release-not-routing-eligible",
    "gap:excluded:entity-kind-mismatch",
    "gap:excluded:excluded-community",
    "gap:excluded:missing-required-role",
    "gap:excluded:missing-required-skill",
    "gap:excluded:missing-required-knowledge",
    "gap:excluded:missing-required-tool",
    "gap:excluded:missing-consumed-artifact",
    "gap:excluded:missing-produced-artifact",
    "gap:excluded:missing-required-authority",
    "gap:excluded:forbidden-authority-conflict",
    "gap:excluded:candidate-prohibits-required-authority",
    "gap:excluded:runtime-mismatch",
    "gap:excluded:language-mismatch",
    "gap:excluded:modality-mismatch",
    "gap:excluded:missing-required-community",
    "gap:excluded:required-skill-evidence-below-minimum",
    "gap:excluded:required-tool-evidence-below-minimum",
)
_WORKFORCE_COVERAGE_GAP_CODE_SET = frozenset(WORKFORCE_COVERAGE_GAP_CODES)


def validate_coverage_gap_codes(value: Any) -> list[str]:
    """Validate the public finite aggregate vocabulary without reflecting data."""

    if not isinstance(value, list) or len(value) > len(WORKFORCE_COVERAGE_GAP_CODES):
        raise ValueError("candidate_set_coverage_gaps_invalid")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or item not in _WORKFORCE_COVERAGE_GAP_CODE_SET or item in seen:
            # Do not echo an unknown value: it may contain a candidate identity
            # or other private text from an untrusted remote response.
            raise ValueError("candidate_set_coverage_gaps_invalid")
        seen.add(item)
        result.append(item)
    return result


def validate_candidate_set_coverage_gaps(candidate_set: Mapping[str, Any]) -> None:
    """Validate every candidate-set slot against the public finite vocabulary."""

    slots = candidate_set.get("slots") if isinstance(candidate_set, Mapping) else None
    if not isinstance(slots, list) or not slots:
        raise ValueError("candidate_set_coverage_gaps_invalid")
    for slot in slots:
        if not isinstance(slot, Mapping) or not isinstance(slot.get("slotId"), str):
            raise ValueError("candidate_set_coverage_gaps_invalid")
        validate_coverage_gap_codes(slot.get("coverageGaps"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    normalized = ID_SAFE_RE.sub("-", str(value or "").strip().lower().replace("_", "-")).strip("-.")
    if not normalized:
        normalized = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{normalized[:220]}"


def normalized_strings(value: Any, *, limit: int = 256) -> list[str]:
    if value is None:
        return []
    items: Iterable[Any]
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set, frozenset)):
        items = value
    else:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text[:500])
        if len(result) >= limit:
            break
    return result


def concept_ids(value: Any, prefix: str) -> list[str]:
    result: list[str] = []
    for item in normalized_strings(value):
        concept = item if ":" in item else stable_id(prefix, item)
        if concept not in result:
            result.append(concept)
    return result


def content_tokens(*values: Any) -> set[str]:
    text_parts: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            text_parts.extend(str(item) for item in value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            text_parts.extend(str(item) for item in value)
        elif value is not None:
            text_parts.append(str(value))
    text = " ".join(text_parts).lower().replace("_", " ").replace("-", " ")
    tokens = {match.group(0) for match in TOKEN_RE.finditer(text)}
    hangul = [token for token in tokens if re.fullmatch(r"[가-힣]{2,}", token)]
    for token in hangul:
        tokens.update(token[index : index + 2] for index in range(len(token) - 1))
    return tokens


@lru_cache(maxsize=4)
def load_ontology(path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path) if path else Path(__file__).with_name("ontology_v1.json")
    raw = source.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if data.get("schemaVersion") != "agentlas.workforce-ontology.v1":
        raise ValueError("unsupported workforce ontology")
    if path is None:
        observed_hash = hashlib.sha256(raw).hexdigest()
        if observed_hash != WORKFORCE_ONTOLOGY_SNAPSHOT_SHA256:
            raise ValueError("packaged workforce ontology snapshot hash mismatch")
        if data.get("ontologyVersion") != WORKFORCE_ONTOLOGY_VERSION:
            raise ValueError("packaged workforce ontology version mismatch")
    return data


def assertion_concepts(assertions: Any) -> set[str]:
    if not isinstance(assertions, list):
        return set()
    return {
        str(item.get("concept"))
        for item in assertions
        if isinstance(item, Mapping) and item.get("concept")
    }


def tool_concepts(assertions: Any) -> set[str]:
    if not isinstance(assertions, list):
        return set()
    return {
        str(item.get("capability"))
        for item in assertions
        if isinstance(item, Mapping) and item.get("capability")
    }


def verify_profile_integrity(profile: Mapping[str, Any]) -> None:
    provenance = profile.get("provenance") if isinstance(profile.get("provenance"), Mapping) else {}
    expected = canonical_digest({"semantic": profile.get("semantic"), "qualification": profile.get("qualification")})
    if provenance.get("contentDigest") != expected:
        raise ValueError("workforce profile content digest mismatch")
    package_hash = str(profile.get("packageHash") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", package_hash):
        raise ValueError("workforce profile package hash is invalid")
