"""Small JSON-RPC client for the public Agentlas Hub MCP endpoint."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from ..auth import ensure_access_token
from .bootstrap import networking_home, read_json

_HUB_TIMEOUT_SECONDS = 15
_HUB_CAPABILITY_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_HUB_TOOL_MAX_RESPONSE_BYTES = 64 * 1024 * 1024


class HubToolError(RuntimeError):
    """Raised when the Hub MCP endpoint returns a protocol or tool error."""


class HubAuthRequiredError(HubToolError):
    """Raised when the Hub says this tool needs an Agentlas sign-in."""


def hub_url(home: Path | str | None = None) -> str:
    base = Path(home) if home else networking_home()
    config = read_json(base / "config.json", default={}) or {}
    return str(config.get("hub_url") or "https://agentlas.cloud").rstrip("/")


def call_hub_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    home: Path | str | None = None,
    timeout: int = _HUB_TIMEOUT_SECONDS,
    auto_auth: bool = True,
) -> dict[str, Any]:
    """Call an Agentlas Hub MCP tool and return its parsed JSON payload."""

    base_url = hub_url(home)
    token = ensure_access_token(base_url, interactive=False)
    try:
        return _call_hub_tool_once(name, arguments or {}, base_url=base_url, timeout=timeout, token=token)
    except HubAuthRequiredError:
        if not auto_auth:
            raise
        token = ensure_access_token(base_url, interactive=True)
        if not token:
            raise
        return _call_hub_tool_once(name, arguments or {}, base_url=base_url, timeout=timeout, token=token)


def list_hub_tools(
    *,
    home: Path | str | None = None,
    timeout: int = _HUB_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    """Probe standard MCP capabilities without opening an interactive login."""

    base_url = hub_url(home)
    token = ensure_access_token(base_url, interactive=False)
    url = base_url + "/api/mcp/v1"
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "hephaestus-network-capability-probe",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(
                _read_bounded_response(
                    response,
                    maximum=_HUB_CAPABILITY_MAX_RESPONSE_BYTES,
                    label="hub capability probe",
                ).decode("utf-8")
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise HubAuthRequiredError("hub capability probe requires Agentlas sign-in") from exc
        raise HubToolError(f"hub capability probe failed: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise HubToolError(f"hub capability probe failed: {exc}") from exc
    if not isinstance(payload, Mapping) or payload.get("error"):
        raise HubToolError("hub capability probe returned a protocol error")
    result = payload.get("result")
    tools = result.get("tools") if isinstance(result, Mapping) else None
    if not isinstance(tools, list) or any(not isinstance(item, Mapping) for item in tools):
        raise HubToolError("hub capability probe returned no tool list")
    return [dict(item) for item in tools]


def _call_hub_tool_once(
    name: str,
    arguments: dict[str, Any],
    *,
    base_url: str,
    timeout: int,
    token: str | None,
) -> dict[str, Any]:
    url = base_url + "/api/mcp/v1"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "hephaestus-network-hub-invoke",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(
                _read_bounded_response(
                    response,
                    maximum=_HUB_TOOL_MAX_RESPONSE_BYTES,
                    label=f"hub tool {name}",
                ).decode("utf-8")
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise HubAuthRequiredError(f"hub tool {name} requires Agentlas sign-in") from exc
        raise HubToolError(f"hub tool {name} failed: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise HubToolError(f"hub tool {name} failed: {exc}") from exc

    if not isinstance(payload, dict):
        raise HubToolError(f"hub tool {name} returned a non-object response")
    if payload.get("error"):
        if _is_auth_required(payload.get("error")):
            raise HubAuthRequiredError(f"hub tool {name} requires Agentlas sign-in")
        raise HubToolError(f"hub tool {name} error: {payload['error']}")

    result = payload.get("result")
    if not isinstance(result, dict):
        raise HubToolError(f"hub tool {name} returned no result object")
    if result.get("isError"):
        text = _first_text(result)
        if _is_auth_required(text or result):
            raise HubAuthRequiredError(f"hub tool {name} requires Agentlas sign-in")
        raise HubToolError(f"hub tool {name} error: {text or result}")

    text = _first_text(result)
    if text is not None:
        try:
            parsed = json.loads(text)
        except ValueError as exc:
            raise HubToolError(f"hub tool {name} returned non-JSON text") from exc
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    return result


def _read_bounded_response(response: Any, *, maximum: int, label: str) -> bytes:
    """Reject oversized Hub responses before or during allocation."""

    headers = getattr(response, "headers", None)
    raw_length = headers.get("Content-Length") if headers is not None else None
    if raw_length is not None:
        try:
            content_length = int(raw_length)
        except (TypeError, ValueError) as exc:
            raise HubToolError(f"{label} returned an invalid Content-Length") from exc
        if content_length < 0 or content_length > maximum:
            raise HubToolError(f"{label} response_too_large")
    payload = response.read(maximum + 1)
    if len(payload) > maximum:
        raise HubToolError(f"{label} response_too_large")
    return payload


def _is_auth_required(value: Any) -> bool:
    if isinstance(value, dict):
        haystack = json.dumps(value, ensure_ascii=False).lower()
    else:
        haystack = str(value or "").lower()
        try:
            parsed = json.loads(haystack)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            haystack = json.dumps(parsed, ensure_ascii=False).lower()
    return "auth_required" in haystack or "authentication required" in haystack or "sign-in" in haystack


def _first_text(result: dict[str, Any]) -> str | None:
    content = result.get("content")
    if not isinstance(content, list):
        return None
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            return str(item.get("text") or "")
    return None
