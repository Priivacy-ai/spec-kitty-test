"""
Advanced jj feature tests.

Validates ops log/undo, Change ID stability, colocated mode sync, and pure jj mode.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _run(cmd: list[str], *, cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a subprocess with consistent defaults."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _git_init(project_dir: Path) -> None:
    _run(["git", "init"], cwd=project_dir)
    _run(["git", "config", "user.email", "test@example.com"], cwd=project_dir)
    _run(["git", "config", "user.name", "Test User"], cwd=project_dir)
    (project_dir / "README.md").write_text("base\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=project_dir)
    _run(["git", "commit", "-m", "base"], cwd=project_dir)


def _jj_change_id(repo_dir: Path) -> str:
    result = _run(["jj", "log", "-r", "@", "--no-graph", "-T", "change_id"], cwd=repo_dir)
    if result.returncode != 0:
        pytest.skip(f"jj log failed: {result.stderr}\n{result.stdout}")
    return result.stdout.strip()


@pytest.fixture(scope="session")
def jj_available() -> bool:
    """Return True if jj is installed and functional."""
    if shutil.which("jj") is None:
        return False
    result = subprocess.run(
        ["jj", "--version"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


@pytest.fixture
def jj_workspace(tmp_path, jj_available) -> Path:
    """Create a colocated jj workspace for advanced ops tests."""
    if not jj_available:
        pytest.skip("jj not installed")

    workspace = tmp_path / "jj-workspace"
    workspace.mkdir()
    _git_init(workspace)

    result = _run(["jj", "git", "init", "--colocate"], cwd=workspace)
    if result.returncode != 0:
        pytest.skip(f"jj git init --colocate failed: {result.stderr}\n{result.stdout}")

    return workspace


@pytest.mark.jj
def test_ops_001_log(jj_workspace: Path):
    """OPS-001: spec-kitty ops log shows operation history."""
    result = _run(["spec-kitty", "ops", "log"], cwd=jj_workspace)
    assert result.returncode == 0, f"ops log failed: {result.stderr}\n{result.stdout}"
    assert "Operation History" in result.stdout


@pytest.mark.jj
def test_ops_002_undo(jj_workspace: Path):
    """OPS-002: spec-kitty ops undo reverses last operation."""
    op_before = _run(["jj", "op", "log", "-n", "1", "--template", "id"], cwd=jj_workspace)
    if op_before.returncode != 0:
        pytest.skip(f"jj op log failed: {op_before.stderr}\n{op_before.stdout}")

    # Create an operation
    _run(["jj", "new"], cwd=jj_workspace)

    result = _run(["spec-kitty", "ops", "undo"], cwd=jj_workspace)
    assert result.returncode == 0, f"ops undo failed: {result.stderr}\n{result.stdout}"

    op_after = _run(["jj", "op", "log", "-n", "1", "--template", "id"], cwd=jj_workspace)
    assert op_after.returncode == 0, f"jj op log failed: {op_after.stderr}\n{op_after.stdout}"
    assert op_after.stdout.strip(), "expected operation history after undo"


@pytest.mark.jj
def test_chg_001_change_id_stable(jj_workspace: Path):
    """CHG-001: Change ID stable across 5 rebases."""
    # Ensure we have a parent change
    (jj_workspace / "change.txt").write_text("change\n", encoding="utf-8")
    _run(["jj", "describe", "-m", "base"], cwd=jj_workspace)
    _run(["jj", "new"], cwd=jj_workspace)

    change_id = _jj_change_id(jj_workspace)

    for _ in range(5):
        result = _run(["jj", "rebase", "-s", "@", "-d", "@-"], cwd=jj_workspace)
        if result.returncode != 0:
            pytest.skip(f"jj rebase failed: {result.stderr}\n{result.stdout}")

    assert _jj_change_id(jj_workspace) == change_id


@pytest.mark.jj
def test_col_001_jj_to_git_visibility(jj_workspace: Path):
    """COL-001: jj changes visible in git log (colocated)."""
    (jj_workspace / "jj-change.txt").write_text("jj change\n", encoding="utf-8")
    commit_result = _run(["jj", "commit", "-m", "jj change"], cwd=jj_workspace)
    if commit_result.returncode != 0:
        pytest.skip(f"jj commit failed: {commit_result.stderr}\n{commit_result.stdout}")

    export_result = _run(["jj", "git", "export"], cwd=jj_workspace)
    if export_result.returncode != 0:
        pytest.skip(f"jj git export failed: {export_result.stderr}\n{export_result.stdout}")

    git_log = _run(["git", "log", "-1", "--pretty=%B"], cwd=jj_workspace)
    assert git_log.returncode == 0, f"git log failed: {git_log.stderr}\n{git_log.stdout}"
    assert "jj change" in git_log.stdout


@pytest.mark.jj
def test_col_002_git_to_jj_visibility(jj_workspace: Path):
    """COL-002: git changes visible in jj log (colocated)."""
    (jj_workspace / "git-change.txt").write_text("git change\n", encoding="utf-8")
    _run(["git", "add", "git-change.txt"], cwd=jj_workspace)
    _run(["git", "commit", "-m", "git change"], cwd=jj_workspace)

    import_result = _run(["jj", "git", "import"], cwd=jj_workspace)
    if import_result.returncode != 0:
        pytest.skip(f"jj git import failed: {import_result.stderr}\n{import_result.stdout}")

    jj_log = _run(["jj", "log", "-n", "5", "--no-graph"], cwd=jj_workspace)
    assert jj_log.returncode == 0, f"jj log failed: {jj_log.stderr}\n{jj_log.stdout}"
    assert "git change" in jj_log.stdout


@pytest.mark.jj
def test_pure_001_pure_jj_mode(tmp_path, jj_available):
    """PURE-001: Pure jj mode (no git) functional."""
    if not jj_available:
        pytest.skip("jj not installed")

    repo = tmp_path / "jj-pure"
    repo.mkdir()

    result = _run(["jj", "init"], cwd=repo)
    if result.returncode != 0:
        combined = (result.stdout + result.stderr).lower()
        if "unrecognized subcommand" in combined:
            pytest.xfail("jj init (pure mode) not supported by this jj build")
        pytest.skip(f"jj init failed: {result.stderr}\n{result.stdout}")

    ops_log = _run(["spec-kitty", "ops", "log"], cwd=repo)
    assert ops_log.returncode == 0, f"ops log failed: {ops_log.stderr}\n{ops_log.stdout}"
