from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from agentlas_cloud.memory_hook import MAX_CAPSULE_CHARS, build_capsule, write_cache
from ontology import OntologyRuntime, RuntimeConfig


ROOT = Path(__file__).resolve().parents[1]
FAKE_SECRET = "fixture_secret_value_123456"


class MemoryHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        (self.root / ".agentlas").mkdir(parents=True)
        self.db_path = self.root / ".agentlas" / "ontology-runtime.sqlite"
        source = self.root / "decisions.md"
        source.write_text(
            "Database rollback requires schema verification. "
            f"api_key={FAKE_SECRET} must never be recalled.",
            encoding="utf-8",
        )
        OntologyRuntime(RuntimeConfig(db_path=self.db_path)).ingest_path(source)
        self.root = self.root.resolve()
        self.db_path = self.root / ".agentlas" / "ontology-runtime.sqlite"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _install_agent_projection(self) -> Path:
        agentlas_home = Path(self.tmp.name) / "agentlas-home"
        projection = (
            agentlas_home
            / "networking"
            / "hub-agents"
            / "release-writer"
            / "memory"
            / "experience.sqlite"
        )
        projection.parent.mkdir(parents=True)
        runtime = OntologyRuntime(RuntimeConfig(db_path=projection))
        runtime.ingest_experience(
            agent_id="hub:release-writer",
            summary="For database rollback, write concise migration notes after verification.",
            tags=["database", "rollback"],
            source_memory_id="release-1",
        )
        runtime.ingest_experience(
            agent_id="hub:other-agent",
            summary="Other agent private database rollback instructions must stay isolated.",
            tags=["database", "rollback"],
            source_memory_id="other-1",
        )
        agent_card = self.root / ".agentlas" / "agent-card.json"
        agent_card.write_text(json.dumps({"slug": "release-writer"}), encoding="utf-8")
        agent_card_hash = hashlib.sha256(agent_card.read_bytes()).hexdigest()
        (self.root / ".agentlas" / "routing-card.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "routing-card/2.0",
                    "routing_status": "routing_ready",
                    "agent_card_ref": {
                        "slug": "release-writer",
                        "path": ".agentlas/agent-card.json",
                        "content_hash": agent_card_hash,
                    },
                }
            ),
            encoding="utf-8",
        )
        return agentlas_home

    def test_capsule_is_local_bounded_redacted_and_agent_isolated(self) -> None:
        agentlas_home = self._install_agent_projection()
        with closing(
            sqlite3.connect(
                agentlas_home / "networking/hub-agents/release-writer/memory/experience.sqlite"
            )
        ) as conn:
            before = tuple(
                conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("memory_candidates", "memory_links", "working_memory", "memory_candidate_events")
            )

        with patch.dict(os.environ, {"AGENTLAS_HOME": str(agentlas_home)}):
            capsule, workspace = build_capsule(
                {"cwd": str(self.root), "user_prompt": "How should database rollback work?"}
            )

        self.assertEqual(workspace, self.root)
        self.assertIsNotNone(capsule)
        assert capsule is not None
        self.assertLessEqual(len(capsule), MAX_CAPSULE_CHARS)
        self.assertIn('<agentlas-memory-context version="1" digest="sha256:', capsule)
        self.assertIn("schema verification", capsule)
        self.assertIn("concise migration notes", capsule)
        self.assertNotIn(FAKE_SECRET, capsule)
        self.assertIn("api_key=[REDACTED]", capsule)
        self.assertNotIn("Other agent private", capsule)
        self.assertIn("writes=disabled; network=disabled", capsule)

        with closing(
            sqlite3.connect(
                agentlas_home / "networking/hub-agents/release-writer/memory/experience.sqlite"
            )
        ) as conn:
            after = tuple(
                conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("memory_candidates", "memory_links", "working_memory", "memory_candidate_events")
            )
        self.assertEqual(before, after, "recall must not create memory tickets or hot-cache rows")

    def test_outside_agentlas_project_skips_cleanly(self) -> None:
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        capsule, workspace = build_capsule({"cwd": str(outside), "user_prompt": "rollback"})
        self.assertIsNone(capsule)
        self.assertEqual(workspace, outside.resolve())

    def test_native_host_policy_files_are_not_reinjected(self) -> None:
        policy = self.root / "AGENTS.md"
        policy.write_text(
            "HOST_POLICY_DUPLICATE_SENTINEL database rollback instructions.",
            encoding="utf-8",
        )
        OntologyRuntime(RuntimeConfig(db_path=self.db_path)).ingest_path(policy)
        capsule, _ = build_capsule(
            {
                "cwd": str(self.root),
                "user_prompt": "HOST_POLICY_DUPLICATE_SENTINEL database rollback",
            }
        )
        self.assertIsNotNone(capsule)
        assert capsule is not None
        self.assertNotIn("HOST_POLICY_DUPLICATE_SENTINEL", capsule)
        self.assertIn("schema verification", capsule)

    def test_unverified_agent_card_cannot_open_private_projection(self) -> None:
        agentlas_home = self._install_agent_projection()
        routing_path = self.root / ".agentlas" / "routing-card.json"
        routing = json.loads(routing_path.read_text(encoding="utf-8"))
        routing["agent_card_ref"]["content_hash"] = "0" * 64
        routing_path.write_text(json.dumps(routing), encoding="utf-8")
        with patch.dict(os.environ, {"AGENTLAS_HOME": str(agentlas_home)}):
            capsule, _ = build_capsule(
                {"cwd": str(self.root), "user_prompt": "database rollback"}
            )
        self.assertIsNotNone(capsule)
        assert capsule is not None
        self.assertNotIn("concise migration notes", capsule)
        self.assertNotIn("Other agent private", capsule)

    def test_verified_agent_projection_recalls_without_project_ontology(self) -> None:
        agentlas_home = self._install_agent_projection()
        self.db_path.unlink()
        with patch.dict(os.environ, {"AGENTLAS_HOME": str(agentlas_home)}):
            capsule, workspace = build_capsule(
                {"cwd": str(self.root), "user_prompt": "database rollback"}
            )
        self.assertEqual(workspace, self.root)
        self.assertIsNotNone(capsule)
        assert capsule is not None
        self.assertIn("concise migration notes", capsule)
        self.assertNotIn("Other agent private", capsule)

    def test_claude_output_uses_additional_context_contract(self) -> None:
        result = subprocess.run(
            [
                str(ROOT / "bin" / "agentlas-memory-hook"),
                "--host",
                "claude",
                "--event",
                "UserPromptSubmit",
                "--cwd",
                str(self.root),
                "--prompt",
                "database rollback",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        specific = payload["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "UserPromptSubmit")
        self.assertTrue(specific["additionalContext"].startswith("<agentlas-memory-context"))

    def test_claude_and_codex_plugin_roots_and_event_contracts(self) -> None:
        temp_home = Path(self.tmp.name) / "plugin-home"
        temp_home.mkdir()
        runtime_environments = (
            ("claude", "CLAUDE_PLUGIN_ROOT"),
            ("codex", "CODEX_PLUGIN_ROOT"),
            ("codex", "CLAUDE_PLUGIN_ROOT"),
        )
        for runtime, root_variable in runtime_environments:
            plugin_root = ROOT / runtime / "plugins" / "agentlas-core-engine-meta-agent"
            hooks = json.loads(
                (plugin_root / "hooks" / "hooks.json").read_text(encoding="utf-8")
            )
            for event in ("SessionStart", "UserPromptSubmit"):
                with self.subTest(runtime=runtime, event=event):
                    command = hooks["hooks"][event][0]["hooks"][0]["command"]
                    self.assertIn(root_variable, command)
                    self.assertIn(f"--host {runtime}", command)
                    other_variable = (
                        "CODEX_PLUGIN_ROOT"
                        if root_variable == "CLAUDE_PLUGIN_ROOT"
                        else "CLAUDE_PLUGIN_ROOT"
                    )
                    env = dict(os.environ)
                    env.pop(root_variable, None)
                    env.pop(other_variable, None)
                    env.update({root_variable: str(plugin_root), "HOME": str(temp_home)})
                    result = subprocess.run(
                        ["/bin/sh", "-c", command],
                        input=json.dumps(
                            {
                                "cwd": str(self.root),
                                "hook_event_name": event,
                                "user_prompt": "database rollback",
                            }
                        ),
                        cwd=self.root,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=True,
                    )
                    payload = json.loads(result.stdout)
                    specific = payload["hookSpecificOutput"]
                    self.assertEqual(specific["hookEventName"], event)
                    self.assertIn("schema verification", specific["additionalContext"])
        self.assertFalse((temp_home / ".agentlas" / "runtime-memory-context").exists())

    def test_plugin_hook_missing_root_fails_open_with_json(self) -> None:
        for runtime, root_variable in (
            ("claude", "CLAUDE_PLUGIN_ROOT"),
            ("codex", "CODEX_PLUGIN_ROOT"),
        ):
            plugin_root = ROOT / runtime / "plugins" / "agentlas-core-engine-meta-agent"
            hooks = json.loads(
                (plugin_root / "hooks" / "hooks.json").read_text(encoding="utf-8")
            )
            command = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
            env = dict(os.environ)
            env.pop("CLAUDE_PLUGIN_ROOT", None)
            env.pop("CODEX_PLUGIN_ROOT", None)
            with self.subTest(runtime=runtime):
                result = subprocess.run(
                    ["/bin/sh", "-c", command],
                    input='{"cwd":"/tmp","user_prompt":"rollback"}',
                    cwd=self.root,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=True,
                )
                self.assertEqual(json.loads(result.stdout), {})
                self.assertNotIn(root_variable, result.stderr)

    def test_isolated_codex_plugin_bundle_uses_verified_model_asset(self) -> None:
        source_plugin = ROOT / "codex" / "plugins" / "agentlas-core-engine-meta-agent"
        isolated_plugin = Path(self.tmp.name) / "isolated-cache" / "hephaestus"
        shutil.copytree(source_plugin, isolated_plugin)
        hooks = json.loads(
            (isolated_plugin / "hooks" / "hooks.json").read_text(encoding="utf-8")
        )
        command = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        isolated_home = Path(self.tmp.name) / "isolated-home"
        isolated_home.mkdir()
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env.pop("PYTHONPATH", None)
        env.update(
            {
                "CODEX_PLUGIN_ROOT": str(isolated_plugin),
                "HOME": str(isolated_home),
            }
        )
        result = subprocess.run(
            ["/bin/sh", "-c", command],
            input=json.dumps(
                {
                    "cwd": str(self.root),
                    "hook_event_name": "UserPromptSubmit",
                    "user_prompt": "database rollback",
                }
            ),
            cwd=isolated_home,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        capsule = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("retrieval=local_model", capsule)
        self.assertIn("adapter=model2vec_potion_base_8m_int8_hybrid", capsule)
        self.assertFalse((isolated_home / ".agentlas" / "runtime").exists())

    def test_executable_fails_open_when_runtime_import_fails(self) -> None:
        fake_python = Path(self.tmp.name) / "fake-python"
        fake_python.write_text(
            "#!/bin/sh\n"
            "case \"$*\" in\n"
            "  *'import sys'*) exit 0 ;;\n"
            "  *) exit 42 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake_python.chmod(0o755)
        env = dict(os.environ)
        env["HEPHAESTUS_PYTHON"] = str(fake_python)
        result = subprocess.run(
            [str(ROOT / "bin" / "agentlas-memory-hook"), "--host", "claude"],
            input='{"cwd":"/tmp"}',
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "{}")

    def test_grok_cache_index_keeps_workspace_boundary(self) -> None:
        cache = Path(self.tmp.name) / "cache"
        capsule, workspace = build_capsule({"cwd": str(self.root), "user_prompt": "database rollback"})
        assert workspace is not None and capsule is not None
        with patch.dict(os.environ, {"AGENTLAS_MEMORY_CACHE_DIR": str(cache)}):
            capsule_path = write_cache("grok", workspace, capsule)
        self.assertIsNotNone(capsule_path)
        index = (cache / "grok" / "index.md").read_text(encoding="utf-8")
        self.assertIn(f'Workspace JSON: {json.dumps(str(self.root.resolve()))}', index)
        self.assertIn(str(capsule_path), index)
        self.assertNotIn(FAKE_SECRET, Path(capsule_path).read_text(encoding="utf-8"))
        self.assertEqual(stat.S_IMODE(cache.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((cache / "grok").stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(Path(capsule_path).stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((cache / "grok" / "index.md").stat().st_mode), 0o600)

        hostile = Path(self.tmp.name) / "workspace`\n- injected: true"
        hostile.mkdir()
        with patch.dict(os.environ, {"AGENTLAS_MEMORY_CACHE_DIR": str(cache)}):
            write_cache("grok", hostile, capsule)
        index = (cache / "grok" / "index.md").read_text(encoding="utf-8")
        self.assertIn("workspace`\\n- injected: true", index)
        self.assertNotIn("\n- injected: true\n", index)


if __name__ == "__main__":
    unittest.main()
