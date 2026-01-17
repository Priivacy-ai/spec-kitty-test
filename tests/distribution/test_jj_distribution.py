"""
Distribution tests for jujutsu (jj) integration.

These tests validate installed-package behavior without template overrides.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest


def _with_git_identity(env: dict[str, str]) -> dict[str, str]:
    """Ensure git can commit without relying on global config."""
    env = env.copy()
    env.setdefault("GIT_AUTHOR_NAME", "Spec Kitty")
    env.setdefault("GIT_AUTHOR_EMAIL", "spec-kitty@example.com")
    env.setdefault("GIT_COMMITTER_NAME", "Spec Kitty")
    env.setdefault("GIT_COMMITTER_EMAIL", "spec-kitty@example.com")
    return env


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a subprocess with consistent defaults."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _init_project(project_path: Path, env: dict[str, str]) -> None:
    """Initialize a project via spec-kitty init with no template bypass."""
    result = _run(
        [
            "spec-kitty",
            "init",
            "--here",
            "--ai=codex",
            "--ignore-agent-tools",
        ],
        cwd=project_path,
        env=env,
        timeout=90,
    )
    if result.returncode != 0:
        pytest.fail(f"spec-kitty init failed: {result.stderr}\n{result.stdout}")


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


def _ensure_meta_json(feature_dir: Path) -> None:
    """Create a minimal meta.json if none exists."""
    meta_path = feature_dir / "meta.json"
    if meta_path.exists():
        return
    feature_number = feature_dir.name.split("-")[0]
    meta = {
        "feature_number": feature_number,
        "slug": feature_dir.name,
        "mission": "software-dev",
        "created_at": "2026-01-01T00:00:00Z",
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def _write_wp(feature_dir: Path, wp_id: str = "WP01") -> Path:
    """Create a minimal WP file with frontmatter."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    wp_path = tasks_dir / f"{wp_id}-jj.md"
    wp_body = f"""---
work_package_id: "{wp_id}"
title: "JJ Distribution Test"
lane: "planned"
subtasks: []
dependencies: []
phase: "Phase 1 - Distribution"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history: []
---

# Work Package Prompt: {wp_id} – JJ Distribution Test
"""
    wp_path.write_text(wp_body, encoding="utf-8")
    return wp_path


def _commit_feature_artifacts(project_path: Path, env: dict[str, str]) -> None:
    """Commit feature artifacts so implement doesn't need to auto-commit."""
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


@pytest.mark.distribution
@pytest.mark.jj
def test_dist_001_init_without_bypass(tmp_path, no_template_bypass, require_jj):
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    project = tmp_path / "project"
    project.mkdir()

    env = _with_git_identity(no_template_bypass)
    _init_project(project, env)
    _configure_git_identity(project, env)

    assert (project / ".kittify").exists(), "spec-kitty init should create .kittify"


@pytest.mark.distribution
@pytest.mark.jj
def test_dist_002_vcs_detection_from_pypi(tmp_path, no_template_bypass, require_jj):
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    project = tmp_path / "project"
    project.mkdir()

    env = _with_git_identity(no_template_bypass)
    _init_project(project, env)
    _configure_git_identity(project, env)
    _ensure_jj_repo(project, env)

    feature_dir = _create_feature(project, env, "jj-dist")
    _ensure_meta_json(feature_dir)

    from specify_cli.cli.commands import implement as implement_cmd
    from specify_cli.core.vcs.types import VCSBackend

    backend = implement_cmd._ensure_vcs_in_meta(feature_dir, project)
    assert backend == VCSBackend.JUJUTSU

    meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta.get("vcs") == "jj"
    assert meta.get("vcs_locked_at"), "vcs_locked_at should be set"


@pytest.mark.distribution
@pytest.mark.jj
def test_dist_003_workspace_creation(tmp_path, no_template_bypass, require_jj):
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    project = tmp_path / "project"
    project.mkdir()

    env = _with_git_identity(no_template_bypass)
    _init_project(project, env)
    _configure_git_identity(project, env)
    _ensure_jj_repo(project, env)

    feature_dir = _create_feature(project, env, "jj-workspace")
    _ensure_meta_json(feature_dir)
    _write_wp(feature_dir, "WP01")
    _commit_feature_artifacts(project, env)

    feature_slug = feature_dir.name
    result = _run(
        ["spec-kitty", "implement", "WP01", "--feature", feature_slug],
        cwd=project,
        env=env,
        timeout=120,
    )
    if result.returncode != 0:
        pytest.fail(f"spec-kitty implement failed: {result.stderr}\n{result.stdout}")

    workspace_path = project / ".worktrees" / f"{feature_slug}-WP01"
    assert workspace_path.exists(), "workspace should be created"


@pytest.mark.distribution
@pytest.mark.jj
def test_dist_004_python_cli_templates(tmp_path, no_template_bypass, require_jj):
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    project = tmp_path / "project"
    project.mkdir()

    env = _with_git_identity(no_template_bypass)
    _init_project(project, env)
    _configure_git_identity(project, env)

    prompts_dir = project / ".codex" / "prompts"
    assert prompts_dir.exists(), "codex prompt directory should be created"

    template_files = list(prompts_dir.glob("*.md"))
    assert template_files, "expected codex prompt templates"

    bad_refs = []
    cli_templates = 0
    script_ref_re = re.compile(r"[\w\-.]+\.(?:sh|ps1)\b")

    for template in template_files:
        content = template.read_text(encoding="utf-8")
        if script_ref_re.search(content):
            bad_refs.append(template.name)
        if "spec-kitty" in content:
            cli_templates += 1

    assert not bad_refs, f"templates should not reference shell scripts: {bad_refs}"
    assert cli_templates >= 3, "expected multiple templates using spec-kitty CLI"


@pytest.mark.distribution
@pytest.mark.jj
def test_dist_005_no_import_errors(no_template_bypass, require_jj):
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in os.environ
    modules = [
        "specify_cli.core.vcs",
        "specify_cli.core.vcs.detection",
        "specify_cli.core.vcs.exceptions",
        "specify_cli.core.vcs.git",
        "specify_cli.core.vcs.jujutsu",
        "specify_cli.core.vcs.protocol",
        "specify_cli.core.vcs.types",
    ]

    for module_name in modules:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            pytest.fail(f"import failed for {module_name}: {exc}")
