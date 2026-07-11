from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAFETY_SCRIPT = ROOT / "scripts" / "public_safety_check.sh"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy2(SAFETY_SCRIPT, repo / "scripts" / SAFETY_SCRIPT.name)
    assert run("git", "init", "-q", cwd=repo).returncode == 0
    return repo


def test_public_safety_blocks_opencrab_mcp_credentials(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    credential = "ocm_" + ("A" * 28)
    (repo / "connection.txt").write_text(
        "https://opencrab.sh/api/mcp/" + credential + "\n",
        encoding="utf-8",
    )

    result = run("bash", "scripts/public_safety_check.sh", cwd=repo)

    assert result.returncode != 0
    assert "OpenCrab MCP credential" in result.stderr


def test_public_safety_allows_redacted_opencrab_configuration(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "connection.txt").write_text(
        "OPENCRAB_MCP_URL is loaded from the local credential vault.\n"
        "Example: https://opencrab.sh/api/mcp/[REDACTED]\n",
        encoding="utf-8",
    )

    result = run("bash", "scripts/public_safety_check.sh", cwd=repo)

    assert result.returncode == 0, result.stderr
    assert "Public safety check passed." in result.stdout
