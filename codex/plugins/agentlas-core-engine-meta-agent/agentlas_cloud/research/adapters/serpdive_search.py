"""Optional SERPdive search cartridge.

SERPdive returns extracted, answer-ready page content for each result rather
than snippets. The adapter only runs when selected by policy and a key is
configured; queries are sent to an external service.
"""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agentlas_cloud.networking.bootstrap import utc_now

from ..contracts import ResearchAttempt, ResearchModuleManifest, ResearchRequest, ResearchResult, _stable_hash
from ..policy import DEFAULT_MAX_BYTES
from ..redaction import redacted_exception_reason


SERPDIVE_SEARCH_URL = "https://api.serpdive.com/v1/search"


class SerpdiveSearchAdapter:
    module_id = "search.serpdive"
    capabilities = ("search.web", "read.search_results")
    weight = "external_light"
    manifest = ResearchModuleManifest(
        module_id=module_id,
        capabilities=list(capabilities),
        weight=weight,
        slot="search",
        activation="configured",
        requires=["api_key:serpdive", "network:api.serpdive.com"],
        permissions=["network:api.serpdive.com"],
        default_state="available_if_configured",
        privacy="no_raw_token_to_model; external_search_receives_query",
        failure_modes=["module_unavailable", "rate_limited", "external_search_error", "empty_results"],
        install_hint="Set AGENTLAS_SERPDIVE_API_KEY or SERPDIVE_API_KEY and choose provider=serpdive or loadout=full.",
    )

    def __init__(self, *, timeout_seconds: int = 30, max_bytes: int = DEFAULT_MAX_BYTES, max_results: int = 10):
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.max_results = max_results

    def can_handle(self, source_hint: str, request: ResearchRequest) -> bool:
        return source_hint.lower().startswith("search:serpdive:")

    def read(self, source_hint: str, request: ResearchRequest) -> tuple[ResearchResult | None, ResearchAttempt]:
        query = _search_query(source_hint)
        if not query:
            return None, ResearchAttempt(self.module_id, "error", "empty_serpdive_query", source_hint, weight=self.weight)

        api_key = self._api_key()
        if not api_key:
            return (
                None,
                ResearchAttempt(
                    self.module_id,
                    "module_unavailable",
                    "AGENTLAS_SERPDIVE_API_KEY or SERPDIVE_API_KEY not configured",
                    source_hint,
                    weight=self.weight,
                ),
            )

        try:
            payload = self._fetch_json(query, api_key=api_key)
        except HTTPError as exc:
            reason = _status_reason(exc.code)
            return (
                ResearchResult.blocked(SERPDIVE_SEARCH_URL, reason=reason),
                ResearchAttempt(self.module_id, "blocked", f"{reason}:{exc.code}", SERPDIVE_SEARCH_URL, weight=self.weight),
            )
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            return (
                None,
                ResearchAttempt(self.module_id, "error", redacted_exception_reason(exc, max_length=160), SERPDIVE_SEARCH_URL, weight=self.weight),
            )

        title = f"SERPdive search: {query}"
        items = _result_items(payload, max_results=self.max_results)
        markdown = _results_markdown(items)
        citations = [{"label": title, "url": SERPDIVE_SEARCH_URL}]
        citations.extend({"label": item["title"] or item["url"], "url": item["url"]} for item in items)
        result = ResearchResult(
            source_id=_stable_hash(f"search:serpdive:{query}"),
            url=SERPDIVE_SEARCH_URL,
            title=title,
            platform="web_search",
            content_markdown=markdown,
            extracted_at=utc_now(),
            freshness=request.freshness,
            confidence="usable" if markdown else "weak",
            limits=["external_search", "serpdive_search"],
            citations=citations,
        )
        return result, ResearchAttempt(self.module_id, "ok", f"serpdive_results={len(items)}", SERPDIVE_SEARCH_URL, weight=self.weight)

    def _api_key(self) -> str:
        return os.environ.get("AGENTLAS_SERPDIVE_API_KEY") or os.environ.get("SERPDIVE_API_KEY") or ""

    def _fetch_json(self, query: str, *, api_key: str) -> dict:
        body = json.dumps({"query": query, "max_results": self.max_results}).encode("utf-8")
        req = Request(
            SERPDIVE_SEARCH_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AgentlasResearchEngine/0.1 (+https://agentlas.cloud)",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read(self.max_bytes + 1)
        parsed = json.loads(raw[: self.max_bytes].decode("utf-8", errors="replace"))
        if not isinstance(parsed, dict):
            raise ValueError("unexpected_serpdive_payload")
        return parsed


def _search_query(source_hint: str) -> str:
    return source_hint.split(":", 2)[2].strip() if source_hint.lower().startswith("search:serpdive:") else source_hint.strip()


def _result_items(payload: dict, *, max_results: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for entry in payload.get("results") or []:
        if not isinstance(entry, dict):
            continue
        url = str(entry.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        items.append(
            {
                "title": str(entry.get("title") or "").strip(),
                "url": url,
                "content": str(entry.get("content") or "").strip(),
                "date": str(entry.get("date") or "").strip(),
            }
        )
        if len(items) >= max_results:
            break
    return items


def _results_markdown(items: list[dict[str, str]]) -> str:
    sections: list[str] = []
    for item in items:
        heading = item["title"] or item["url"]
        dated = f" ({item['date']})" if item["date"] else ""
        sections.append(f"## {heading}{dated}\n{item['url']}\n\n{item['content']}".strip())
    return "\n\n".join(sections).strip()


def _status_reason(status: int) -> str:
    if status in {401, 407}:
        return "auth_required"
    if status == 403:
        return "blocked"
    if status == 404:
        return "not_found"
    if status == 429:
        return "rate_limited"
    return "http_error"
