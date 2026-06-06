from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .runtime import DEFAULT_DB_PATH, OntologyRuntime, RuntimeConfig

RUNTIME_CONFIG_FILE = "ontology-runtime.json"
SOURCE_MANIFEST_FILE = "ontology-sources.json"
INBOX_DIR = "ontology-inbox"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ontology", description="Hephaestus local-first ontology runtime")
    parser.add_argument("--db", default=None, help="SQLite runtime database path")
    sub = parser.add_subparsers(dest="command", required=True)

    auto = sub.add_parser("auto", help="Safely activate and sync a project ontology")
    auto.add_argument("project", nargs="?", default=".")
    auto.add_argument("--scope", default="internal", choices=["public", "internal", "private"], help="Default ingest scope")
    auto.add_argument("--no-ingest", action="store_true", help="Only create activation files")

    sources = sub.add_parser("sources", help="Registered source commands")
    sources_sub = sources.add_subparsers(dest="sources_command", required=True)
    source_add = sources_sub.add_parser("add", help="Register one source path for this project")
    source_add.add_argument("path")
    source_add.add_argument("--project", default=".")
    source_add.add_argument("--scope", default="internal", choices=["public", "internal", "private"])
    source_add.add_argument("--kind", default="project", choices=["project", "company", "personal"])
    source_add.add_argument("--no-ingest", action="store_true")
    source_list = sources_sub.add_parser("list", help="List registered source paths")
    source_list.add_argument("--project", default=".")

    ingest = sub.add_parser("ingest", help="Ingest a file or directory")
    ingest.add_argument("path")
    ingest.add_argument("--scope", default="internal", choices=["public", "internal", "private"], help="Access/privacy scope")
    ingest.add_argument("--parent-source-id")

    query = sub.add_parser("query", help="Run GraphRAG query")
    query.add_argument("question")
    query.add_argument("--agent")
    query.add_argument("--scope", action="append", choices=["public", "internal", "private"], help="Allowed scope; repeatable")
    query.add_argument("--limit", type=int, default=5)

    graph = sub.add_parser("graph", help="Graph commands")
    graph_sub = graph.add_subparsers(dest="graph_command", required=True)
    entity = graph_sub.add_parser("entity", help="Show entity graph slice")
    entity.add_argument("name")

    memory = sub.add_parser("memory", help="Memory Curator bridge commands")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)
    candidates = memory_sub.add_parser("candidates", help="List Memory Curator candidate tickets")
    candidates.add_argument("--status")
    decide = memory_sub.add_parser("decide", help="Record candidate review state")
    decide.add_argument("ticket_id")
    decide.add_argument("decision", choices=["approve", "reject", "quarantine", "supersede", "deprecate"])
    decide.add_argument("--reason", required=True)

    working = sub.add_parser("working-memory", help="Agent Working Memory commands")
    working_sub = working.add_subparsers(dest="working_command", required=True)
    read = working_sub.add_parser("read", help="Read agent hot cache")
    read.add_argument("--agent", required=True)
    read.add_argument("--include-expired", action="store_true")
    prune = working_sub.add_parser("prune", help="Expire/evict stale cache entries")
    prune.add_argument("--agent", required=True)
    prune.add_argument("--min-importance", type=float, default=0.0)

    sub.add_parser("verify", help="Run runtime integrity verification")

    storage = sub.add_parser("storage", help="Storage backup/export/import")
    storage_sub = storage.add_subparsers(dest="storage_command", required=True)
    backup = storage_sub.add_parser("backup")
    backup.add_argument("destination")
    export = storage_sub.add_parser("export")
    export.add_argument("destination")
    import_cmd = storage_sub.add_parser("import")
    import_cmd.add_argument("source")

    args = parser.parse_args(argv)

    if args.command == "auto":
        return emit(auto_activate_project(args.project, args.scope, no_ingest=args.no_ingest, db_override=args.db))
    if args.command == "sources" and args.sources_command == "add":
        return emit(register_source(args.project, args.path, args.scope, args.kind, no_ingest=args.no_ingest, db_override=args.db))
    if args.command == "sources" and args.sources_command == "list":
        return emit({"sources": read_source_manifest(project_agentlas_dir(args.project)).get("sources", [])})

    runtime = OntologyRuntime(RuntimeConfig(db_path=Path(args.db or DEFAULT_DB_PATH)))

    if args.command == "ingest":
        return emit(runtime.ingest_path(args.path, access_scope=args.scope, parent_source_id=args.parent_source_id))
    if args.command == "query":
        return emit(runtime.query(args.question, agent_id=args.agent, allowed_scopes=args.scope, limit=args.limit))
    if args.command == "graph" and args.graph_command == "entity":
        return emit(runtime.graph_entity(args.name))
    if args.command == "memory" and args.memory_command == "candidates":
        return emit({"candidates": runtime.list_memory_candidates(status=args.status)})
    if args.command == "memory" and args.memory_command == "decide":
        return emit(runtime.decide_memory_candidate(args.ticket_id, args.decision, args.reason))
    if args.command == "working-memory" and args.working_command == "read":
        return emit({"items": runtime.read_working_memory(args.agent, include_expired=args.include_expired)})
    if args.command == "working-memory" and args.working_command == "prune":
        return emit(runtime.prune_working_memory(args.agent, min_importance=args.min_importance))
    if args.command == "verify":
        result = runtime.verify()
        emit(result)
        return 0 if result["status"] == "pass" else 1
    if args.command == "storage" and args.storage_command == "backup":
        return emit(runtime.backup(args.destination))
    if args.command == "storage" and args.storage_command == "export":
        return emit(runtime.export_json(args.destination))
    if args.command == "storage" and args.storage_command == "import":
        return emit(runtime.import_json(args.source))
    parser.error("unhandled command")
    return 2


def emit(payload: Any) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def project_root(project: str | Path) -> Path:
    return Path(project).expanduser().resolve()


def project_agentlas_dir(project: str | Path) -> Path:
    return project_root(project) / ".agentlas"


def project_db_path(project: str | Path, db_override: str | None = None) -> Path:
    return Path(db_override).expanduser().resolve() if db_override else project_agentlas_dir(project) / "ontology-runtime.sqlite"


def ensure_runtime_files(project: str | Path, default_scope: str = "internal", db_override: str | None = None) -> dict[str, Any]:
    root = project_root(project)
    agentlas_dir = root / ".agentlas"
    inbox = agentlas_dir / INBOX_DIR
    db_path = project_db_path(root, db_override)
    agentlas_dir.mkdir(parents=True, exist_ok=True)
    inbox.mkdir(parents=True, exist_ok=True)

    config_path = agentlas_dir / RUNTIME_CONFIG_FILE
    now_config = {
        "schemaVersion": "1.0",
        "kind": "agentlas-ontology-runtime",
        "state": "active",
        "activation": "automatic",
        "projectRoot": str(root),
        "dbPath": str(db_path),
        "inboxPath": str(inbox),
        "sourceManifest": str(agentlas_dir / SOURCE_MANIFEST_FILE),
        "defaultScope": default_scope,
        "autoIngestPolicy": {
            "mode": "inbox_and_registered_sources_only",
            "neverScanHomeDirectory": True,
            "neverScanSiblingProjects": True,
            "crossProjectSearchDefault": "disabled",
            "privateScopeDefaultSearch": "excluded",
        },
        "memoryPolicy": {
            "durableWrites": "candidate-ticket-only",
            "workingMemory": "runtime-cache-only",
        },
    }
    if not config_path.exists():
        config_path.write_text(json.dumps(now_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_path = agentlas_dir / SOURCE_MANIFEST_FILE
    if not manifest_path.exists():
        manifest_path.write_text(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "kind": "agentlas-ontology-source-manifest",
                    "projectRoot": str(root),
                    "sources": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return {
        "project_root": str(root),
        "agentlas_dir": str(agentlas_dir),
        "config_path": str(config_path),
        "source_manifest_path": str(manifest_path),
        "inbox_path": str(inbox),
        "db_path": str(db_path),
    }


def read_source_manifest(agentlas_dir: Path) -> dict[str, Any]:
    path = agentlas_dir / SOURCE_MANIFEST_FILE
    if not path.exists():
        return {
            "schemaVersion": "1.0",
            "kind": "agentlas-ontology-source-manifest",
            "projectRoot": str(agentlas_dir.parent),
            "sources": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def write_source_manifest(agentlas_dir: Path, manifest: dict[str, Any]) -> None:
    (agentlas_dir / SOURCE_MANIFEST_FILE).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def registered_ingest_paths(project: str | Path) -> list[dict[str, str]]:
    root = project_root(project)
    agentlas_dir = root / ".agentlas"
    manifest = read_source_manifest(agentlas_dir)
    paths: list[dict[str, str]] = []
    inbox = agentlas_dir / INBOX_DIR
    if inbox.exists():
        paths.append({"path": str(inbox), "scope": "internal", "kind": "project_inbox"})
    for item in manifest.get("sources", []):
        source_path = Path(str(item.get("path", ""))).expanduser()
        if source_path.exists():
            paths.append(
                {
                    "path": str(source_path.resolve()),
                    "scope": str(item.get("scope") or "internal"),
                    "kind": str(item.get("kind") or "project"),
                }
            )
    return paths


def auto_activate_project(project: str | Path, scope: str = "internal", no_ingest: bool = False, db_override: str | None = None) -> dict[str, Any]:
    files = ensure_runtime_files(project, scope, db_override)
    runtime = OntologyRuntime(RuntimeConfig(db_path=Path(files["db_path"])))
    sync_results: list[dict[str, Any]] = []
    if not no_ingest:
        for source in registered_ingest_paths(project):
            summary = runtime.ingest_path(source["path"], access_scope=source["scope"])
            sync_results.append(
                {
                    "path": source["path"],
                    "kind": source["kind"],
                    "scope": source["scope"],
                    "chunks_written": summary["chunks_written"],
                    "entities_written": summary["entities_written"],
                    "relations_written": summary["relations_written"],
                    "idempotent_skips": summary["idempotent_skips"],
                    "sources": len(summary["sources"]),
                }
            )
    verify = runtime.verify()
    return {
        "status": "active",
        "project_root": files["project_root"],
        "db_path": files["db_path"],
        "config_path": files["config_path"],
        "inbox_path": files["inbox_path"],
        "source_manifest_path": files["source_manifest_path"],
        "auto_ingest_policy": "inbox_and_registered_sources_only",
        "cross_project_search_default": "disabled",
        "sync_results": sync_results,
        "verify": verify,
    }


def register_source(
    project: str | Path,
    source_path: str | Path,
    scope: str,
    kind: str,
    no_ingest: bool = False,
    db_override: str | None = None,
) -> dict[str, Any]:
    files = ensure_runtime_files(project, scope, db_override)
    agentlas_dir = Path(files["agentlas_dir"])
    manifest = read_source_manifest(agentlas_dir)
    resolved = Path(source_path).expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"source does not exist: {resolved}")
    sources = [item for item in manifest.get("sources", []) if Path(str(item.get("path", ""))).expanduser().resolve() != resolved]
    sources.append({"path": str(resolved), "scope": scope, "kind": kind})
    manifest["sources"] = sources
    write_source_manifest(agentlas_dir, manifest)
    result = {
        "status": "registered",
        "project_root": files["project_root"],
        "source": {"path": str(resolved), "scope": scope, "kind": kind},
        "source_manifest_path": files["source_manifest_path"],
    }
    if not no_ingest:
        runtime = OntologyRuntime(RuntimeConfig(db_path=Path(files["db_path"])))
        result["ingest"] = runtime.ingest_path(resolved, access_scope=scope)
    return result
