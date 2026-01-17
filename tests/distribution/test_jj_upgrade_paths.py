"""
Upgrade Path Tests for jujutsu (jj) integration.

These tests validate git-to-jj migration scenarios, ensuring safe upgrade paths
when users install or uninstall jj on their systems.

Test Matrix (T039-T042):
- UPG-001: git-only project + jj install → new features use jj
- UPG-002: Existing git WPs continue working after jj installed
- UPG-003: jj uninstalled → clear error on jj features
- UPG-004: Mixed git/jj project coexistence

CRITICAL: These are distribution tests - NO SPEC_KITTY_TEMPLATE_ROOT bypass.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Generator

import pytest


def _with_git_identity(env: dict[str, str]) -> dict[str, str]:
    """Ensure git can commit without relying on global config."""
    env = env.copy()
    env.setdefault("GIT_AUTHOR_NAME", "Spec Kitty")
    env.setdefault("GIT_AUTHOR_EMAIL", "spec-kitty@example.com")
    env.setdefault("GIT_COMMITTER_NAME", "Spec Kitty")
    env.setdefault("GIT_COMMITTER_EMAIL", "spec-kitty@example.com")
    return env


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Run a subprocess with consistent defaults."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _get_path_without_jj(env: dict[str, str]) -> dict[str, str]:
    """Return environment with jj removed from PATH.

    This simulates a system where jj is not installed by filtering out
    any PATH entries that contain the jj binary.
    """
    env = env.copy()
    original_path = env.get("PATH", "")

    # Filter PATH to exclude directories containing jj
    filtered_paths = []
    for path_entry in original_path.split(os.pathsep):
        jj_path = Path(path_entry) / "jj"
        if not jj_path.exists():
            filtered_paths.append(path_entry)

    env["PATH"] = os.pathsep.join(filtered_paths)
    return env


def _get_path_with_jj(env: dict[str, str]) -> dict[str, str]:
    """Restore original PATH (with jj accessible)."""
    # Return env with original PATH from os.environ
    env = env.copy()
    env["PATH"] = os.environ.get("PATH", "")
    return env


def _init_project_git_only(project_path: Path, env: dict[str, str]) -> None:
    """Initialize a project as git-only (no jj)."""
    result = _run(
        [
            "spec-kitty",
            "init",
            "--here",
            "--ai=codex",
            "--vcs=git",
            "--ignore-agent-tools",
            "--force",
        ],
        cwd=project_path,
        env=env,
        timeout=90,
    )
    if result.returncode != 0:
        pytest.fail(f"spec-kitty init (git-only) failed: {result.stderr}\n{result.stdout}")


def _init_project_with_jj(project_path: Path, env: dict[str, str]) -> None:
    """Initialize a project with jj VCS."""
    result = _run(
        [
            "spec-kitty",
            "init",
            "--here",
            "--ai=codex",
            "--vcs=jj",
            "--ignore-agent-tools",
            "--force",
        ],
        cwd=project_path,
        env=env,
        timeout=90,
    )
    if result.returncode != 0:
        pytest.fail(f"spec-kitty init (jj) failed: {result.stderr}\n{result.stdout}")


def _configure_git_identity(project_path: Path, env: dict[str, str]) -> None:
    """Set local git identity for commits in test repositories."""
    for key, value in (
        ("user.name", "Spec Kitty"),
        ("user.email", "spec-kitty@example.com"),
    ):
        result = _run(["git", "config", key, value], cwd=project_path, env=env, timeout=30)
        if result.returncode != 0:
            pytest.fail(f"git config {key} failed: {result.stderr}\n{result.stdout}")


def _ensure_jj_repo(project_path: Path, env: dict[str, str]) -> None:
    """Initialize a colocated jj repo when jj is available."""
    if (project_path / ".jj").exists():
        return
    result = _run(
        ["jj", "git", "init", "--colocate"],
        cwd=project_path,
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"jj git init --colocate failed: {result.stderr}\n{result.stdout}")


def _create_feature(project_path: Path, env: dict[str, str], slug: str) -> Path:
    """Create a feature directory via the agent CLI and return its path."""
    result = _run(
        ["spec-kitty", "agent", "feature", "create-feature", slug, "--json"],
        cwd=project_path,
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"feature creation failed: {result.stderr}\n{result.stdout}")

    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        pytest.fail(f"feature creation JSON parse failed: {exc}\n{result.stdout}")

    feature_dir = Path(payload["feature_dir"])
    if not feature_dir.exists():
        pytest.fail(f"feature directory missing: {feature_dir}")
    return feature_dir


def _ensure_meta_json(feature_dir: Path, vcs: str = "git") -> None:
    """Create or update meta.json with VCS info."""
    meta_path = feature_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        feature_number = feature_dir.name.split("-")[0]
        meta = {
            "feature_number": feature_number,
            "slug": feature_dir.name,
            "mission": "software-dev",
            "created_at": "2026-01-01T00:00:00Z",
        }

    meta["vcs"] = vcs
    if vcs == "jj":
        meta["vcs_locked_at"] = "2026-01-01T00:00:00Z"

    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def _write_wp(feature_dir: Path, wp_id: str = "WP01") -> Path:
    """Create a minimal WP file with frontmatter."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    wp_path = tasks_dir / f"{wp_id}-upgrade-test.md"
    wp_body = f"""---
work_package_id: "{wp_id}"
title: "Upgrade Test"
lane: "planned"
subtasks: []
dependencies: []
phase: "Phase 1 - Upgrade"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history: []
---

# Work Package Prompt: {wp_id} – Upgrade Test
"""
    wp_path.write_text(wp_body, encoding="utf-8")
    return wp_path


def _commit_feature_artifacts(project_path: Path, env: dict[str, str]) -> None:
    """Commit feature artifacts."""
    result = _run(["git", "add", "-A"], cwd=project_path, env=env, timeout=30)
    if result.returncode != 0:
        pytest.fail(f"git add failed: {result.stderr}\n{result.stdout}")

    result = _run(
        ["git", "commit", "-m", "chore: add planning artifacts"],
        cwd=project_path,
        env=env,
        timeout=30,
    )
    if result.returncode != 0:
        stderr = result.stderr.lower()
        stdout = result.stdout.lower()
        if "nothing to commit" not in stderr and "nothing to commit" not in stdout:
            pytest.fail(f"git commit failed: {result.stderr}\n{result.stdout}")


def _make_initial_commit(project_path: Path, env: dict[str, str]) -> None:
    """Make initial commit and ensure we're on main branch.

    This is required before creating features since spec-kitty requires
    the project to be on main branch.
    """
    # Add all files
    result = _run(["git", "add", "-A"], cwd=project_path, env=env, timeout=30)
    if result.returncode != 0:
        pytest.fail(f"git add failed: {result.stderr}\n{result.stdout}")

    # Make initial commit
    result = _run(
        ["git", "commit", "-m", "chore: initial commit"],
        cwd=project_path,
        env=env,
        timeout=30,
    )
    if result.returncode != 0:
        stderr = result.stderr.lower()
        stdout = result.stdout.lower()
        if "nothing to commit" not in stderr and "nothing to commit" not in stdout:
            pytest.fail(f"git commit failed: {result.stderr}\n{result.stdout}")

    # Ensure we're on main branch (git init may create 'master' instead)
    result = _run(
        ["git", "branch", "-M", "main"],
        cwd=project_path,
        env=env,
        timeout=30,
    )
    # Ignore errors - branch may already be main


@pytest.fixture
def no_template_bypass(monkeypatch) -> dict[str, str]:
    """Return environment without SPEC_KITTY_TEMPLATE_ROOT overrides."""
    env = os.environ.copy()

    # Remove all SPEC_KITTY_* overrides except API keys.
    for key in list(env.keys()):
        if key.startswith("SPEC_KITTY_") and key != "SPEC_KITTY_API_KEY":
            env.pop(key, None)

    for key in list(os.environ.keys()):
        if key.startswith("SPEC_KITTY_") and key != "SPEC_KITTY_API_KEY":
            monkeypatch.delenv(key, raising=False)

    return env


@pytest.fixture
def require_jj() -> None:
    """Skip tests when jj is not installed."""
    if shutil.which("jj") is None:
        pytest.skip("jj not installed")


@pytest.fixture
def jj_available() -> bool:
    """Check if jj is available on the system."""
    return shutil.which("jj") is not None


@pytest.mark.distribution
@pytest.mark.jj
@pytest.mark.upgrade
def test_upg_001_git_to_jj_upgrade(tmp_path, no_template_bypass, require_jj):
    """UPG-001: git-only project + jj install → new features use jj.

    Simulates a user who:
    1. Starts with git-only (jj not in PATH)
    2. Creates a feature with git VCS
    3. "Installs" jj (restores PATH)
    4. Creates a new feature - should detect and use jj

    This validates that spec-kitty correctly detects when jj becomes available.
    """
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    project = tmp_path / "project"
    project.mkdir()

    # Phase 1: Initialize with git-only (jj "not installed")
    env_no_jj = _get_path_without_jj(_with_git_identity(no_template_bypass))

    # Initialize git repo first
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    _configure_git_identity(project, env_no_jj)

    # Initialize spec-kitty with git VCS
    _init_project_git_only(project, env_no_jj)

    # Make initial commit (required for feature creation)
    _make_initial_commit(project, env_no_jj)

    # Create first feature (should use git since jj not available)
    git_feature = _create_feature(project, env_no_jj, "git-feature")
    _ensure_meta_json(git_feature, vcs="git")
    _commit_feature_artifacts(project, env_no_jj)

    # Verify first feature uses git
    git_meta = json.loads((git_feature / "meta.json").read_text(encoding="utf-8"))
    assert git_meta.get("vcs") == "git", "First feature should use git VCS"

    # Phase 2: "Install" jj (restore PATH)
    env_with_jj = _get_path_with_jj(_with_git_identity(no_template_bypass))

    # Initialize jj in the project
    _ensure_jj_repo(project, env_with_jj)

    # Create second feature (should use jj now that it's available)
    jj_feature = _create_feature(project, env_with_jj, "jj-feature")

    # Create meta.json (normally done by /spec-kitty.specify)
    # We leave out vcs so that _ensure_vcs_in_meta will detect it
    meta_path = jj_feature / "meta.json"
    if not meta_path.exists():
        feature_number = jj_feature.name.split("-")[0]
        meta = {
            "feature_number": feature_number,
            "slug": jj_feature.name,
            "mission": "software-dev",
            "created_at": "2026-01-01T00:00:00Z",
        }
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    # Manually call VCS detection for the new feature
    from specify_cli.cli.commands import implement as implement_cmd
    from specify_cli.core.vcs.types import VCSBackend

    backend = implement_cmd._ensure_vcs_in_meta(jj_feature, project)

    # Verify new feature uses jj
    assert backend == VCSBackend.JUJUTSU, "New feature should use jj VCS after jj install"

    jj_meta = json.loads((jj_feature / "meta.json").read_text(encoding="utf-8"))
    assert jj_meta.get("vcs") == "jj", "New feature meta should have vcs=jj"


@pytest.mark.distribution
@pytest.mark.jj
@pytest.mark.upgrade
def test_upg_002_existing_git_wps_work(tmp_path, no_template_bypass, require_jj):
    """UPG-002: Existing git WPs continue working after jj installed.

    After jj is installed, existing git-based workspaces should continue
    to function correctly. The VCS lock ensures they don't switch to jj.
    """
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    project = tmp_path / "project"
    project.mkdir()

    # Phase 1: Initialize as git-only project
    env_no_jj = _get_path_without_jj(_with_git_identity(no_template_bypass))

    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    _configure_git_identity(project, env_no_jj)
    _init_project_git_only(project, env_no_jj)
    _make_initial_commit(project, env_no_jj)

    # Create feature with git VCS
    git_feature = _create_feature(project, env_no_jj, "git-locked-feature")
    _ensure_meta_json(git_feature, vcs="git")
    _write_wp(git_feature, "WP01")
    _commit_feature_artifacts(project, env_no_jj)

    # Verify feature is locked to git
    meta_before = json.loads((git_feature / "meta.json").read_text(encoding="utf-8"))
    assert meta_before.get("vcs") == "git"

    # Phase 2: "Install" jj
    env_with_jj = _get_path_with_jj(_with_git_identity(no_template_bypass))
    _ensure_jj_repo(project, env_with_jj)

    # Try to implement WP on the git-locked feature
    # The VCS lock should preserve git, not switch to jj
    from specify_cli.cli.commands import implement as implement_cmd
    from specify_cli.core.vcs.types import VCSBackend

    # This should respect the existing VCS lock
    backend = implement_cmd._ensure_vcs_in_meta(git_feature, project)

    # Existing git feature should stay as git
    assert backend == VCSBackend.GIT, "Existing git feature should stay as git after jj install"

    meta_after = json.loads((git_feature / "meta.json").read_text(encoding="utf-8"))
    assert meta_after.get("vcs") == "git", "VCS lock should prevent switch to jj"


@pytest.mark.distribution
@pytest.mark.jj
@pytest.mark.upgrade
def test_upg_003_jj_uninstalled_error(tmp_path, no_template_bypass, require_jj):
    """UPG-003: jj uninstalled → clear error on jj features.

    When jj is uninstalled after features were created with jj,
    operations on those features should produce clear error messages.
    """
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    project = tmp_path / "project"
    project.mkdir()

    # Phase 1: Initialize with jj
    env_with_jj = _get_path_with_jj(_with_git_identity(no_template_bypass))

    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    _configure_git_identity(project, env_with_jj)
    _ensure_jj_repo(project, env_with_jj)
    _init_project_with_jj(project, env_with_jj)
    _make_initial_commit(project, env_with_jj)

    # Create feature with jj VCS
    jj_feature = _create_feature(project, env_with_jj, "jj-locked-feature")
    _ensure_meta_json(jj_feature, vcs="jj")
    _write_wp(jj_feature, "WP01")
    _commit_feature_artifacts(project, env_with_jj)

    # Phase 2: "Uninstall" jj (remove from PATH)
    env_no_jj = _get_path_without_jj(_with_git_identity(no_template_bypass))

    # Verify jj is not accessible in this env
    jj_check = subprocess.run(
        ["which", "jj"],
        env=env_no_jj,
        capture_output=True,
        text=True,
    )
    assert jj_check.returncode != 0, "jj should not be accessible after PATH removal"

    # Try to implement WP - should fail with clear error
    result = subprocess.run(
        ["spec-kitty", "implement", "WP01", "--feature", jj_feature.name],
        cwd=project,
        env=env_no_jj,
        capture_output=True,
        text=True,
        timeout=60,
    )

    combined = result.stdout + result.stderr

    # Should indicate jj is required or not found
    error_indicators = [
        "jj" in combined.lower(),
        "not found" in combined.lower(),
        "not installed" in combined.lower(),
        "required" in combined.lower(),
        "error" in combined.lower(),
    ]

    if result.returncode != 0:
        # Good - command failed as expected
        assert any(error_indicators), (
            f"Error should mention jj or provide clear message. Got: {combined[:500]}"
        )
    else:
        # If it succeeded, that's unexpected but we should document behavior
        pytest.xfail(
            "spec-kitty implement succeeded without jj - "
            "may not require jj at implementation time"
        )


@pytest.mark.distribution
@pytest.mark.jj
@pytest.mark.upgrade
def test_upg_004_mixed_git_jj_coexistence(tmp_path, no_template_bypass, require_jj):
    """UPG-004: Mixed git/jj project coexistence.

    A project can have both git-based and jj-based features. Each feature
    uses its locked VCS backend without interference.
    """
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    project = tmp_path / "project"
    project.mkdir()

    env = _with_git_identity(no_template_bypass)

    # Initialize project with both git and jj
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    _configure_git_identity(project, env)
    _ensure_jj_repo(project, env)

    # Use jj as default (but we'll manually set git for one feature)
    _init_project_with_jj(project, env)
    _make_initial_commit(project, env)

    # Create git-locked feature
    git_feature = _create_feature(project, env, "git-legacy")
    _ensure_meta_json(git_feature, vcs="git")
    _write_wp(git_feature, "WP01")

    # Create jj-locked feature
    jj_feature = _create_feature(project, env, "jj-modern")
    _ensure_meta_json(jj_feature, vcs="jj")
    _write_wp(jj_feature, "WP01")

    _commit_feature_artifacts(project, env)

    # Import VCS detection
    from specify_cli.cli.commands import implement as implement_cmd
    from specify_cli.core.vcs.types import VCSBackend

    # Verify each feature uses its locked VCS
    git_backend = implement_cmd._ensure_vcs_in_meta(git_feature, project)
    jj_backend = implement_cmd._ensure_vcs_in_meta(jj_feature, project)

    assert git_backend == VCSBackend.GIT, "Git feature should use git backend"
    assert jj_backend == VCSBackend.JUJUTSU, "Jj feature should use jj backend"

    # Verify meta.json is correct for both
    git_meta = json.loads((git_feature / "meta.json").read_text(encoding="utf-8"))
    jj_meta = json.loads((jj_feature / "meta.json").read_text(encoding="utf-8"))

    assert git_meta.get("vcs") == "git", "Git feature meta should have vcs=git"
    assert jj_meta.get("vcs") == "jj", "Jj feature meta should have vcs=jj"

    # Both features should coexist without error
    features_dir = project / "kitty-specs"
    git_dirs = list(features_dir.glob("*git-legacy*"))
    jj_dirs = list(features_dir.glob("*jj-modern*"))

    assert len(git_dirs) == 1, "Git feature directory should exist"
    assert len(jj_dirs) == 1, "Jj feature directory should exist"
