"""Typed source-scope adapter for Workforce federation."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Callable, Mapping

from ..networking.hub_client import HubAuthRequiredError, HubToolError, call_hub_tool, list_hub_tools
from .contracts import canonical_digest, canonical_json
from .federation import (
    LineageVerifier,
    WORKFORCE_SOURCE_FAILURE_CODES,
    federate_candidate_sets,
    sources_for_scope,
)
from .federation_store import FederationSessionError, FederationSessionStore
from .index import WorkforceIndex
from .local_registry import LocalWorkforceRegistry
from .privacy import assert_hub_work_order_boundary
from .provenance import validate_federated_selection_wrapper


RemoteSearch = Callable[[str, Mapping[str, Any], list[str]], Mapping[str, Any]]
RemoteBundleFetch = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]
RemoteBundleVerifier = Callable[[str, Mapping[str, Any], Mapping[str, Any]], bool]
RemoteCapabilities = Callable[[], list[Mapping[str, Any]]]

WORKFORCE_SOURCE_BUNDLE_RECEIPT_SCHEMA = "agentlas.workforce-source-bundle-verification.v1"
WORKFORCE_SOURCE_BUNDLE_TOOL = "workforce.fetch_runtime_bundle"
_WORKFORCE_SEARCH_DISCOVERY_NAMES = frozenset(
    {"workforce.search_candidates", "workforce_search_candidates"}
)
_WORKFORCE_BUNDLE_DISCOVERY_NAMES = frozenset(
    {WORKFORCE_SOURCE_BUNDLE_TOOL, "workforce_fetch_runtime_bundle"}
)
WORKFORCE_SOURCE_BUNDLE_FAILURE_CODES = frozenset(
    {
        "source_bundle_fetch_not_supported",
        "source_bundle_fetch_failed",
        "source_bundle_verification_failed",
        "source_bundle_claim_mismatch",
        "source_not_supported",
        "source_unauthorized",
        "source_forbidden",
        "source_timeout",
        "source_rate_limited",
        "insufficient_credits",
        "owner_only",
        "no_cloud_package",
        "agent_not_found",
    }
)


class WorkforceSourceError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _finite_failure(code: str) -> str:
    return code if code in WORKFORCE_SOURCE_FAILURE_CODES else "source_unavailable"


class WorkforceSourceService:
    """Collect source-owned menus, then invoke the source-neutral federation."""

    def __init__(
        self,
        *,
        local_registry: LocalWorkforceRegistry | None = None,
        session_store: FederationSessionStore | None = None,
        remote_search: RemoteSearch | None = None,
        remote_bundle_fetch: RemoteBundleFetch | None = None,
        remote_bundle_verifier: RemoteBundleVerifier | None = None,
        remote_capabilities: RemoteCapabilities | None = None,
        lineage_verifier: LineageVerifier | None = None,
        cloud_source_supported: bool | None = None,
        reconcile_local: bool = True,
    ):
        self.local_registry = local_registry or LocalWorkforceRegistry()
        self.session_store = session_store or FederationSessionStore(lineage_verifier=lineage_verifier)
        if self.session_store.lineage_verifier is not lineage_verifier and lineage_verifier is not None:
            raise WorkforceSourceError("lineage_verifier_store_mismatch")
        self._uses_default_remote_search = remote_search is None
        self.remote_search = remote_search or self._default_remote_search
        self._uses_default_remote_bundle_fetch = remote_bundle_fetch is None
        self.remote_bundle_fetch = remote_bundle_fetch or self._default_remote_bundle_fetch
        self.remote_bundle_verifier = remote_bundle_verifier or self._default_remote_bundle_verifier
        self.remote_capabilities = remote_capabilities or list_hub_tools
        self._remote_capability_cache: list[Mapping[str, Any]] | None = None
        self.lineage_verifier = lineage_verifier or self.session_store.lineage_verifier
        # None means capability-negotiated. Explicit False is useful for an
        # offline/older deployment that must not be probed.
        self.cloud_source_supported = cloud_source_supported
        self.reconcile_local = reconcile_local

    def _cloud_supported(self) -> bool:
        if self.cloud_source_supported is not None:
            return self.cloud_source_supported
        if self._remote_capability_cache is None:
            try:
                self._remote_capability_cache = list(self.remote_capabilities())
            except (HubToolError, OSError, TimeoutError, TypeError, ValueError):
                self._remote_capability_cache = []
        search = next(
            (
                row
                for row in self._remote_capability_cache
                if isinstance(row, Mapping)
                and row.get("name") in _WORKFORCE_SEARCH_DISCOVERY_NAMES
            ),
            None,
        )
        schema = search.get("inputSchema") if isinstance(search, Mapping) else None
        properties = schema.get("properties") if isinstance(schema, Mapping) else None
        source_scope = properties.get("sourceScope") if isinstance(properties, Mapping) else None
        scopes = source_scope.get("enum") if isinstance(source_scope, Mapping) else None
        names = {
            str(row.get("name"))
            for row in self._remote_capability_cache
            if isinstance(row, Mapping) and row.get("name")
        }
        return (
            isinstance(scopes, list)
            and "cloud" in scopes
            and bool(names & _WORKFORCE_BUNDLE_DISCOVERY_NAMES)
        )

    def _default_remote_search(
        self,
        source: str,
        work_order: Mapping[str, Any],
        expand_slot_ids: list[str],
    ) -> Mapping[str, Any]:
        if source == "cloud" and not self._cloud_supported():
            raise WorkforceSourceError("source_not_supported")
        payload: dict[str, Any] = {"workOrder": dict(work_order)}
        if expand_slot_ids:
            payload["expandSlotIds"] = list(expand_slot_ids)
        # Hub keeps its currently deployed payload intact.  Owner Cloud uses a
        # typed extra field and must not silently degrade to public Hub.
        if source == "cloud":
            payload["sourceScope"] = "cloud"
        return call_hub_tool("workforce.search_candidates", payload)

    def _default_remote_bundle_fetch(
        self,
        source: str,
        pin: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Use the exact-release source capability; never replay a merged menu.

        The remote source must resolve the release inside its own immutable
        CandidateSet session.  This deliberately does not call the legacy
        slug/latest bundle endpoint and does not send the federated CandidateSet
        or selection back to a source.
        """

        if source == "cloud" and not self._cloud_supported():
            raise WorkforceSourceError("source_not_supported")
        payload = {
            "sourceSelectionSessionId": pin["sourceSelectionSessionId"],
            "sourceCandidateSetDigest": pin["sourceCandidateSetDigest"],
            "agentDefinitionId": pin["agentDefinitionId"],
            "agentReleaseId": pin["agentReleaseId"],
            "releaseVersion": pin["releaseVersion"],
            "packageHash": pin["packageHash"],
            "contentDigest": pin["contentDigest"],
            "entityKind": pin["entityKind"],
        }
        if source == "cloud":
            payload["sourceScope"] = "cloud"
        return call_hub_tool(WORKFORCE_SOURCE_BUNDLE_TOOL, payload)

    @staticmethod
    def _default_remote_bundle_verifier(
        source: str,
        pin: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> bool:
        receipt = response.get("verificationReceipt")
        bundle = response.get("runtimeBundle")
        if not isinstance(receipt, Mapping) or not isinstance(bundle, Mapping):
            return False
        required = {
            "schemaVersion", "status", "verification", "source",
            "sourceSelectionSessionId", "sourceCandidateSetDigest",
            "agentDefinitionId", "agentReleaseId", "releaseVersion",
            "packageHash", "contentDigest", "entityKind", "receiptDigest",
        }
        if (
            set(receipt) != required
            or receipt.get("schemaVersion") != WORKFORCE_SOURCE_BUNDLE_RECEIPT_SCHEMA
            or receipt.get("status") != "verified"
            or receipt.get("verification") not in {"verified_transport", "verified_signature"}
            or receipt.get("source") != source
            or receipt.get("receiptDigest")
            != canonical_digest({key: value for key, value in receipt.items() if key != "receiptDigest"})
        ):
            return False
        for field in (
            "sourceSelectionSessionId", "sourceCandidateSetDigest",
            "agentDefinitionId", "agentReleaseId", "releaseVersion",
            "packageHash", "contentDigest", "entityKind",
        ):
            if receipt.get(field) != pin.get(field):
                return False
        return all(bundle.get(field) == pin.get(field) for field in ("agentReleaseId", "packageHash", "contentDigest"))

    def _search_remote(
        self,
        source: str,
        work_order: Mapping[str, Any],
        expand_slot_ids: list[str],
    ) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
        try:
            response = self.remote_search(source, work_order, expand_slot_ids)
        except WorkforceSourceError:
            raise
        except HubAuthRequiredError as exc:
            raise WorkforceSourceError("source_unauthorized") from exc
        except TimeoutError as exc:
            raise WorkforceSourceError("source_timeout") from exc
        except HubToolError as exc:
            raise WorkforceSourceError("source_unavailable") from exc
        except (OSError, ValueError) as exc:
            raise WorkforceSourceError("source_unavailable") from exc
        if not isinstance(response, Mapping):
            raise WorkforceSourceError("source_invalid_candidate_set")
        if isinstance(response.get("status"), str) and response.get("status") in WORKFORCE_SOURCE_FAILURE_CODES:
            raise WorkforceSourceError(str(response["status"]))
        if source == "cloud":
            source_receipt = response.get("sourceReceipt")
            source_claim = response.get("sourceScope") == "cloud" or (
                isinstance(source_receipt, Mapping) and source_receipt.get("source") == "cloud"
            )
            if not source_claim:
                # An older server may ignore the new sourceScope argument and
                # return a public Hub menu. Never relabel that as owner Cloud.
                raise WorkforceSourceError("source_not_supported")
        candidate_set = response.get("candidateSet") if isinstance(response.get("candidateSet"), Mapping) else response
        lineages = response.get("lineageAttestations") if isinstance(response.get("lineageAttestations"), Mapping) else {}
        return dict(candidate_set), {
            str(key): dict(value)
            for key, value in lineages.items()
            if isinstance(value, Mapping)
        }

    def search(
        self,
        work_order: Mapping[str, Any],
        *,
        source_scope: str = "network",
        expand_slot_ids: list[str] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        sources = sources_for_scope(source_scope)
        # WorkOrder v1 is the existing content-only/redacted contract.  It is
        # enforced before any remote call and consistently for Local today.
        assert_hub_work_order_boundary(work_order)
        # Freeze the exact accepted object once. The same canonical bytes drive
        # every source query, federation identity, and durable session pin.
        accepted_work_order = json.loads(canonical_json(work_order))
        slot_ids = [
            str(slot.get("slotId"))
            for slot in accepted_work_order.get("roleSlots") or []
            if isinstance(slot, Mapping) and slot.get("slotId")
        ]
        if not slot_ids:
            raise WorkforceSourceError("work_order_slots_missing")
        candidate_sets: dict[str, dict[str, Any]] = {}
        failures: dict[str, str] = {}
        lineages: dict[str, dict[str, Mapping[str, Any]]] = {}
        expand = list(expand_slot_ids or [])
        for source in sources:
            if source == "local":
                try:
                    if self.reconcile_local:
                        self.local_registry.reconcile()
                    index = WorkforceIndex(self.local_registry.active_profiles())
                    candidate_sets["local"] = index.search_candidates(
                        accepted_work_order,
                        now=now,
                        expand_slot_ids=expand,
                    )
                    lineages["local"] = self.local_registry.lineage_attestations()
                except (OSError, ValueError):
                    failures["local"] = "source_unavailable"
                continue
            if source == "cloud" and self.cloud_source_supported is False and self._uses_default_remote_search:
                failures["cloud"] = "source_not_supported"
                continue
            try:
                candidate_set, source_lineages = self._search_remote(source, accepted_work_order, expand)
                candidate_sets[source] = candidate_set
                lineages[source] = source_lineages
            except WorkforceSourceError as exc:
                failures[source] = _finite_failure(exc.code)

        policy = (
            accepted_work_order.get("selectionPolicy")
            if isinstance(accepted_work_order.get("selectionPolicy"), Mapping)
            else {}
        )
        policy_minimum = policy.get("minimumCandidatesPerSlot")
        minimum_candidates = (
            policy_minimum
            if isinstance(policy_minimum, int) and not isinstance(policy_minimum, bool) and 1 <= policy_minimum <= 30
            else 2
        )
        policy_maximum = policy.get("maximumCandidatesPerSlot")
        maximum_candidates = (
            policy_maximum
            if isinstance(policy_maximum, int) and not isinstance(policy_maximum, bool) and 1 <= policy_maximum <= 100
            else 100
        )
        result = federate_candidate_sets(
            candidate_sets,
            scope=source_scope,
            work_order_id=str(accepted_work_order.get("workOrderId") or ""),
            ontology_version=str(accepted_work_order.get("ontologyVersion") or ""),
            slot_ids=slot_ids,
            source_failures=failures,
            lineage_attestations=lineages,
            lineage_verifier=self.lineage_verifier,
            minimum_candidates_per_slot=minimum_candidates,
            maximum_candidates_per_slot=maximum_candidates,
            now=now,
        )
        successful_sources = {
            str(row["source"])
            for row in result.get("sourceReceipts") or []
            if isinstance(row, Mapping) and row.get("status") == "succeeded"
        }
        self.session_store.save(
            result,
            work_order=accepted_work_order,
            source_candidate_sets={source: candidate_sets[source] for source in successful_sources},
            now=now,
        )
        return result

    def fetch_selected_runtime_bundles(
        self,
        federated_selection: Mapping[str, Any],
        *,
        work_order: Mapping[str, Any],
        selection: Mapping[str, Any],
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch only exact selected releases using their original source pins."""

        session_id = str(federated_selection.get("selectionSessionId") or "")
        try:
            work_order_digest = self.session_store.assert_work_order_binding(
                session_id,
                work_order,
                now=now,
            )
        except FederationSessionError as exc:
            raise WorkforceSourceError("federated_work_order_binding_mismatch") from exc
        try:
            selection_digest = canonical_digest(selection)
        except (TypeError, ValueError) as exc:
            raise WorkforceSourceError("federated_selection_exact_binding_mismatch") from exc
        if (
            federated_selection.get("workOrderDigest") != work_order_digest
            or federated_selection.get("selectionDigest") != selection_digest
        ):
            raise WorkforceSourceError("federated_selection_exact_binding_mismatch")
        validate_federated_selection_wrapper(federated_selection)
        self.session_store.get(session_id, now=now)
        stored_selection = self.session_store.get_federated_selection(
            session_id,
            str(federated_selection.get("federatedSelectionDigest") or ""),
            now=now,
        )
        if canonical_digest(stored_selection) != canonical_digest(federated_selection):
            raise WorkforceSourceError("federated_selection_store_binding_mismatch")
        result: list[dict[str, Any]] = []
        bundle_cache: dict[tuple[str, ...], dict[str, Any]] = {}
        for raw_pin in federated_selection.get("selectedSourcePins") or []:
            pin = dict(raw_pin)
            authoritative_pin = self.session_store.source_pin(
                session_id,
                slot_id=str(pin.get("slotId") or ""),
                agent_definition_id=str(pin.get("agentDefinitionId") or ""),
                agent_release_id=str(pin.get("agentReleaseId") or ""),
                now=now,
            )
            if pin != authoritative_pin:
                raise WorkforceSourceError("selected_release_source_pin_mismatch")
            source = str(pin.get("source") or "")
            source_candidate_set = self.session_store.source_candidate_set(session_id, source, now=now)
            source_candidate = next(
                (
                    candidate
                    for slot in source_candidate_set.get("slots") or []
                    if isinstance(slot, Mapping) and slot.get("slotId") == pin.get("slotId")
                    for candidate in slot.get("candidates") or []
                    if isinstance(candidate, Mapping)
                    and candidate.get("agentDefinitionId") == pin.get("agentDefinitionId")
                    and candidate.get("agentReleaseId") == pin.get("agentReleaseId")
                ),
                None,
            )
            if not isinstance(source_candidate, Mapping) or any(
                source_candidate.get(field) != pin.get(field)
                for field in ("releaseVersion", "packageHash", "contentDigest", "entityKind")
            ):
                raise WorkforceSourceError("selected_release_source_pin_mismatch")
            bundle_key = (
                source,
                str(pin.get("sourceSelectionSessionId") or ""),
                str(pin.get("sourceCandidateSetDigest") or ""),
                str(pin.get("agentDefinitionId") or ""),
                str(pin.get("agentReleaseId") or ""),
                str(pin.get("releaseVersion") or ""),
                str(pin.get("packageHash") or ""),
                str(pin.get("contentDigest") or ""),
                str(pin.get("entityKind") or ""),
            )
            cached = bundle_cache.get(bundle_key)
            if cached is not None:
                bundle = dict(cached)
            elif source == "local":
                try:
                    bundle = self.local_registry.runtime_bundle(str(pin["agentReleaseId"]))
                except KeyError as exc:
                    detail = str(exc.args[0]) if exc.args else ""
                    raise WorkforceSourceError(
                        detail if detail.startswith("local_") else "source_bundle_fetch_failed"
                    ) from exc
                except OSError as exc:
                    raise WorkforceSourceError("source_bundle_fetch_failed") from exc
                bundle = dict(bundle)
                bundle_cache[bundle_key] = dict(bundle)
            else:
                try:
                    response = dict(self.remote_bundle_fetch(source, pin))
                except WorkforceSourceError:
                    raise
                except HubAuthRequiredError as exc:
                    raise WorkforceSourceError("source_unauthorized") from exc
                except HubToolError as exc:
                    message = str(exc).lower()
                    code = (
                        "source_bundle_fetch_not_supported"
                        if any(marker in message for marker in ("unknown tool", "not found", "unsupported"))
                        else "source_bundle_fetch_failed"
                    )
                    raise WorkforceSourceError(code) from exc
                except (OSError, TimeoutError, ValueError) as exc:
                    raise WorkforceSourceError("source_bundle_fetch_failed") from exc
                refusal = response.get("status")
                if not isinstance(response.get("runtimeBundle"), Mapping) and isinstance(refusal, str):
                    raise WorkforceSourceError(
                        refusal if refusal in WORKFORCE_SOURCE_BUNDLE_FAILURE_CODES else "source_bundle_fetch_failed"
                    )
                bundle = response.get("runtimeBundle")
                receipt = response.get("verificationReceipt")
                if (
                    not isinstance(bundle, Mapping)
                    or not isinstance(receipt, Mapping)
                    or self.remote_bundle_verifier(source, pin, response) is not True
                ):
                    raise WorkforceSourceError("source_bundle_verification_failed")
                bundle = dict(bundle)
                bundle_cache[bundle_key] = dict(bundle)
            for field in ("agentReleaseId", "packageHash", "contentDigest"):
                if bundle.get(field) != pin.get(field):
                    raise WorkforceSourceError("source_bundle_claim_mismatch")
            result.append({"sourcePin": pin, "runtimeBundle": bundle})
        return result


def search_workforce_sources(
    work_order: Mapping[str, Any],
    *,
    source_scope: str,
    service: WorkforceSourceService | None = None,
    expand_slot_ids: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    return (service or WorkforceSourceService()).search(
        work_order,
        source_scope=source_scope,
        expand_slot_ids=expand_slot_ids,
        now=now,
    )


__all__ = [
    "WORKFORCE_SOURCE_BUNDLE_RECEIPT_SCHEMA",
    "WORKFORCE_SOURCE_BUNDLE_FAILURE_CODES",
    "WORKFORCE_SOURCE_BUNDLE_TOOL",
    "WorkforceSourceError",
    "WorkforceSourceService",
    "search_workforce_sources",
]
