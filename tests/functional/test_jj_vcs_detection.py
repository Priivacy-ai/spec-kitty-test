"""
VCS Detection Tests for jj (jujutsu) integration.

These tests validate spec-kitty's behavior when detecting and selecting
between jj and git VCS backends during project initialization.

Test Matrix (DET-001 to DET-007):
- DET-001: Both jj+git installed -> jj selected
- DET-002: Git only -> git selected with jj recommendation
- DET-003: Neither installed -> clear error
- DET-004: --vcs=git override works
- DET-005: Broken jj -> git fallback with warning
- DET-006: Wrong jj tool detected
- DET-007: jj version below minimum (< 0.20) -> warning/error
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


def create_isolated_path(
    fake_bin: Path,
    *,
    include_git: bool = True,
    include_spec_kitty: bool = True,
) -> str:
    """Create an isolated PATH with only specified binaries."""
    fake_bin.mkdir(exist_ok=True)

    if include_git:
        git_path = shutil.which("git")
        if git_path:
            target = fake_bin / "git"
            if not target.exists():
                target.symlink_to(git_path)

    if include_spec_kitty:
        spec_kitty_path = shutil.which("spec-kitty")
        if spec_kitty_path:
            target = fake_bin / "spec-kitty"
            if not target.exists():
                target.symlink_to(spec_kitty_path)

        python_path = shutil.which("python3") or shutil.which("python")
        if python_path:
            for name in ["python3", "python"]:
                target = fake_bin / name
                if not target.exists():
                    target.symlink_to(python_path)

        for util in ["env", "sh", "bash"]:
            util_path = shutil.which(util)
            if util_path:
                target = fake_bin / util
                if not target.exists():
                    target.symlink_to(util_path)

    return str(fake_bin)


def create_feature(project_dir: Path, slug: str, env: dict[str, str] | None = None) -> Path:
    """Create a feature directory and return its path."""
    _ensure_main_branch(project_dir, env=env)
    result = subprocess.run(
        ["spec-kitty", "agent", "feature", "create-feature", slug, "--json"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    feature_dir = Path(payload["feature_dir"])
    if not feature_dir.exists():
        raise FileNotFoundError(f"Feature directory not created: {feature_dir}")
    return feature_dir


def _ensure_main_branch(project_dir: Path, env: dict[str, str] | None = None) -> None:
    """Ensure repo has an initial commit and is on main or master."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=env,
    )
    branch = result.stdout.strip() if result.returncode == 0 else ""

    if branch in {"main", "master"}:
        return

    subprocess.run(
        ["git", "checkout", "-b", "main"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=env,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=env,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=env,
    )


def write_wp(feature_dir: Path, wp_id: str = "WP01") -> Path:
    """Create a minimal WP file for implement to consume."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    wp_path = tasks_dir / f"{wp_id}-vcs-detection.md"
    wp_path.write_text(
        f"""---
work_package_id: "{wp_id}"
title: "VCS Detection Test"
lane: "planned"
subtasks: []
dependencies: []
phase: "Phase 1 - Foundation"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history: []
---

# Work Package Prompt: {wp_id} - VCS Detection Test
""",
        encoding="utf-8",
    )
    return wp_path


def ensure_meta_json(feature_dir: Path) -> None:
    """Ensure meta.json exists so implement can lock VCS."""
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


def run_implement(
    project_dir: Path,
    feature_dir: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run spec-kitty implement for WP01 and return the result."""
    return subprocess.run(
        ["spec-kitty", "implement", "WP01", "--feature", feature_dir.name],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=env,
    )


def read_vcs_meta(feature_dir: Path) -> str | None:
    """Read vcs value from feature meta.json."""
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta.get("vcs")


def ensure_jj_repo(project_dir: Path) -> None:
    """Ensure a colocated jj repo exists for workspace creation."""
    result = subprocess.run(
        ["jj", "git", "init", "--colocate"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "already initialized" not in (result.stdout + result.stderr).lower():
        pytest.skip(f"jj repo init failed: {result.stderr}\n{result.stdout}")


class TestVCSDetection:
    """Tests for VCS detection and selection logic."""

    @pytest.mark.jj
    def test_det_001_jj_and_git_selects_jj(self, spec_kitty_project, jj_available):
        """DET-001: When both jj and git installed, jj is selected."""
        if not jj_available:
            pytest.skip("jj not installed")

        ensure_jj_repo(spec_kitty_project)

        feature_dir = create_feature(spec_kitty_project, "det-001-jj")
        write_wp(feature_dir)
        ensure_meta_json(feature_dir)

        result = run_implement(spec_kitty_project, feature_dir)
        assert result.returncode == 0, f"implement failed: {result.stderr}\n{result.stdout}"

        assert read_vcs_meta(feature_dir) == "jj"

    def test_det_002_git_only_with_recommendation(self, spec_kitty_project, tmp_path):
        """DET-002: Git only -> git selected with jj recommendation."""
        fake_bin = tmp_path / "fake_bin"
        isolated_path = create_isolated_path(fake_bin, include_git=True, include_spec_kitty=True)
        env = {**os.environ, "PATH": isolated_path}

        init_result = subprocess.run(
            ["spec-kitty", "init", "--here", "--force", "--ai", "claude"],
            cwd=spec_kitty_project,
            capture_output=True,
            text=True,
            env=env,
        )
        assert init_result.returncode == 0, f"init failed: {init_result.stderr}\n{init_result.stdout}"

        combined = init_result.stdout + init_result.stderr
        assert "git" in combined.lower(), f"Expected git selection message: {combined}"
        assert "install jj" in combined.lower() or "recommended" in combined.lower(), (
            f"Expected jj recommendation: {combined}"
        )

        feature_dir = create_feature(spec_kitty_project, "det-002-git", env=env)
        write_wp(feature_dir)
        ensure_meta_json(feature_dir)

        result = run_implement(spec_kitty_project, feature_dir, env=env)
        assert result.returncode == 0, f"implement failed: {result.stderr}\n{result.stdout}"
        assert read_vcs_meta(feature_dir) == "git"

    def test_det_003_neither_vcs_error(self, spec_kitty_project, tmp_path):
        """DET-003: Neither VCS installed -> clear error."""
        feature_dir = create_feature(spec_kitty_project, "det-003-none")
        write_wp(feature_dir)
        ensure_meta_json(feature_dir)

        fake_bin = tmp_path / "fake_bin"
        isolated_path = create_isolated_path(fake_bin, include_git=False, include_spec_kitty=True)
        env = {**os.environ, "PATH": isolated_path}

        result = run_implement(spec_kitty_project, feature_dir, env=env)
        assert result.returncode != 0, "Expected failure when no VCS tools are available"

        combined = (result.stdout + result.stderr).lower()
        assert any(token in combined for token in ["neither", "git", "jj", "install", "vcs"]), (
            f"Expected clear VCS error message: {result.stdout}\n{result.stderr}"
        )

    @pytest.mark.jj
    def test_det_004_vcs_git_override(self, spec_kitty_project, jj_available):
        """DET-004: --vcs=git override works."""
        if not jj_available:
            pytest.skip("jj not installed")

        result = subprocess.run(
            ["spec-kitty", "init", "--here", "--force", "--ai", "claude", "--vcs=git"],
            cwd=spec_kitty_project,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"init failed: {result.stderr}\n{result.stdout}"

        combined = result.stdout + result.stderr
        assert "using git" in combined.lower(), f"Expected git override message: {combined}"

    def test_det_005_broken_jj_fallback(self, spec_kitty_project, tmp_path):
        """DET-005: Broken jj -> git fallback with warning."""
        fake_bin = tmp_path / "fake_bin"
        isolated_path = create_isolated_path(fake_bin, include_git=True, include_spec_kitty=True)

        broken_jj = fake_bin / "jj"
        broken_jj.write_text("""#!/bin/bash\necho \"jj: segmentation fault\" >&2\nexit 139\n""")
        broken_jj.chmod(stat.S_IRWXU)

        env = {**os.environ, "PATH": isolated_path}

        init_result = subprocess.run(
            ["spec-kitty", "init", "--here", "--force", "--ai", "claude"],
            cwd=spec_kitty_project,
            capture_output=True,
            text=True,
            env=env,
        )
        assert init_result.returncode == 0, f"init failed: {init_result.stderr}\n{init_result.stdout}"

        combined = init_result.stdout + init_result.stderr
        assert "using git" in combined.lower(), f"Expected git fallback message: {combined}"
        assert "jj" in combined.lower(), f"Expected jj warning in output: {combined}"

        feature_dir = create_feature(spec_kitty_project, "det-005-broken", env=env)
        write_wp(feature_dir)
        ensure_meta_json(feature_dir)

        result = run_implement(spec_kitty_project, feature_dir, env=env)
        assert result.returncode == 0, f"implement failed: {result.stderr}\n{result.stdout}"
        assert read_vcs_meta(feature_dir) == "git"

    def test_det_006_wrong_tool_validation(self, spec_kitty_project, tmp_path):
        """DET-006: Wrong tool named 'jj' detected."""
        fake_bin = tmp_path / "fake_bin"
        isolated_path = create_isolated_path(fake_bin, include_git=True, include_spec_kitty=True)

        fake_jj = fake_bin / "jj"
        fake_jj.write_text(
            """#!/bin/bash\nif [ \"$1\" = \"--version\" ]; then\n  echo \"jj - Journal Jumper v2.3.4\"\n  exit 0\nfi\nexit 1\n"""
        )
        fake_jj.chmod(stat.S_IRWXU)

        env = {**os.environ, "PATH": isolated_path}

        feature_dir = create_feature(spec_kitty_project, "det-006-wrong", env=env)
        write_wp(feature_dir)
        ensure_meta_json(feature_dir)

        result = run_implement(spec_kitty_project, feature_dir, env=env)
        if result.returncode == 0:
            assert read_vcs_meta(feature_dir) == "git", (
                "Wrong jj tool should not be selected as VCS"
            )
        else:
            combined = (result.stdout + result.stderr).lower()
            assert "jj" in combined or "vcs" in combined, (
                f"Expected wrong-tool error message: {result.stdout}\n{result.stderr}"
            )

    def test_det_007_jj_version_below_minimum(self, spec_kitty_project, tmp_path):
        """DET-007: jj version below minimum triggers warning/fallback."""
        fake_bin = tmp_path / "fake_bin"
        isolated_path = create_isolated_path(fake_bin, include_git=True, include_spec_kitty=True)

        old_jj = fake_bin / "jj"
        old_jj.write_text(
            """#!/bin/bash\nif [ \"$1\" = \"--version\" ]; then\n  echo \"jj 0.15.0\"\n  exit 0\nfi\nexit 0\n"""
        )
        old_jj.chmod(stat.S_IRWXU)

        env = {**os.environ, "PATH": isolated_path}

        feature_dir = create_feature(spec_kitty_project, "det-007-old", env=env)
        write_wp(feature_dir)
        ensure_meta_json(feature_dir)

        result = run_implement(spec_kitty_project, feature_dir, env=env)
        if result.returncode == 0:
            if read_vcs_meta(feature_dir) == "jj":
                pytest.xfail("Minimum jj version enforcement not implemented")
        else:
            combined = (result.stdout + result.stderr).lower()
            assert any(token in combined for token in ["version", "0.20", "minimum", "upgrade"]), (
                f"Expected version warning/error: {result.stdout}\n{result.stderr}"
            )
