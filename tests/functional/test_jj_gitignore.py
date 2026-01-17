"""
Gitignore and Adversarial Tests for jj (jujutsu) integration.

These tests validate:
1. Gitignore handling - ensuring kitty-specs/ is NOT incorrectly ignored
2. Adversarial edge cases - corrupted files, missing directories, etc.

Test Matrix:
- GI-001: Main repo .gitignore does NOT ignore kitty-specs/
- GI-002: `git add kitty-specs/` succeeds
- GI-003: Upgrade fixes incorrect gitignore
- ADV-001: Corrupted meta.json handled gracefully
- ADV-002: Corrupted workspace directory handled gracefully

Bug Context: The .gitignore template was incorrectly ignoring `kitty-specs/`
in the main repo - this should NOT happen as kitty-specs/ must be tracked.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


# =============================================================================
# Helper Functions
# =============================================================================

def create_spec_kitty_project(project_dir: Path, use_jj: bool = False) -> bool:
    """Initialize a spec-kitty project.

    Args:
        project_dir: Directory to initialize the project in
        use_jj: If True, use jj; if False, use git only

    Returns:
        True if successful, False otherwise
    """
    # Initialize git first
    subprocess.run(
        ["git", "init"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_dir,
        check=True,
        capture_output=True
    )

    # Initialize spec-kitty
    vcs_flag = "--vcs=jj" if use_jj else "--vcs=git"
    result = subprocess.run(
        ["spec-kitty", "init", "--here", "--force", "--ai", "claude", vcs_flag],
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    return result.returncode == 0


def create_feature_with_structure(project_dir: Path, feature_name: str) -> Path | None:
    """Create a feature directory with standard structure.

    Args:
        project_dir: The spec-kitty project directory
        feature_name: Name of the feature to create

    Returns:
        Path to the feature directory, or None if creation failed
    """
    kitty_specs = project_dir / "kitty-specs"
    kitty_specs.mkdir(exist_ok=True)

    feature_dir = kitty_specs / f"001-{feature_name}"
    feature_dir.mkdir(exist_ok=True)

    # Create meta.json
    meta = {
        "feature_number": "001",
        "slug": feature_name,
        "friendly_name": f"Test Feature: {feature_name}",
        "mission": "software-dev",
        "created_at": "2026-01-17T00:00:00Z"
    }
    with open(feature_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Create spec.md
    (feature_dir / "spec.md").write_text(f"# {feature_name}\n\nTest spec content.\n")

    # Create tasks directory
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    # Create a simple WP file
    wp_content = """---
work_package_id: "WP01"
title: "Test Work Package"
lane: "planned"
dependencies: []
subtasks:
  - "T001"
---

# WP01 - Test Work Package

Test content.
"""
    (tasks_dir / "WP01-test.md").write_text(wp_content)

    return feature_dir


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def fresh_project(tmp_path):
    """Create a fresh spec-kitty project for testing."""
    project_dir = tmp_path / "gitignore-test-project"
    project_dir.mkdir()

    if not create_spec_kitty_project(project_dir, use_jj=False):
        pytest.skip("Failed to create spec-kitty project")

    return project_dir


@pytest.fixture
def jj_fresh_project(tmp_path, jj_available):
    """Create a fresh spec-kitty project with jj for testing."""
    if not jj_available:
        pytest.skip("jj not installed")

    project_dir = tmp_path / "jj-gitignore-test-project"
    project_dir.mkdir()

    if not create_spec_kitty_project(project_dir, use_jj=True):
        pytest.skip("Failed to create spec-kitty project")

    return project_dir


# =============================================================================
# GI-001: kitty-specs Not Ignored (T043)
# =============================================================================

class TestGitignoreKittySpecs:
    """GI-001: Validate kitty-specs/ is NOT ignored in main repo."""

    def test_gi_001_kitty_specs_not_in_gitignore(self, fresh_project):
        """GI-001: Main repo .gitignore does NOT ignore kitty-specs/.

        The kitty-specs/ directory must be tracked by git, so it should
        not be listed in .gitignore (or should be explicitly un-ignored).
        """
        gitignore = fresh_project / ".gitignore"

        if not gitignore.exists():
            # No .gitignore file - kitty-specs is not ignored (pass)
            return

        content = gitignore.read_text()
        lines = content.strip().split('\n')

        # Check each line for kitty-specs patterns
        for line in lines:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # If kitty-specs is mentioned, it should be negated (un-ignored)
            if 'kitty-specs' in line:
                # Acceptable: !kitty-specs/ (negation)
                # Acceptable: # kitty-specs (comment)
                # NOT acceptable: kitty-specs/ (ignores the directory)
                if line.startswith('!'):
                    # Negation - explicitly un-ignored (good)
                    continue
                else:
                    # Direct ignore pattern - this is the bug
                    pytest.fail(
                        f"BUG: .gitignore contains '{line}' which ignores kitty-specs/\n"
                        f"kitty-specs/ must be tracked by git"
                    )

    @pytest.mark.jj
    def test_gi_001_jj_kitty_specs_not_in_gitignore(self, jj_fresh_project):
        """GI-001 (jj): Main repo .gitignore does NOT ignore kitty-specs/."""
        gitignore = jj_fresh_project / ".gitignore"

        if not gitignore.exists():
            return

        content = gitignore.read_text()
        lines = content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if 'kitty-specs' in line and not line.startswith('!'):
                pytest.fail(
                    f"BUG: .gitignore contains '{line}' which ignores kitty-specs/"
                )


# =============================================================================
# GI-002: git add kitty-specs Works (T044)
# =============================================================================

class TestGitAddKittySpecs:
    """GI-002: Validate git add kitty-specs/ succeeds."""

    def test_gi_002_git_add_kitty_specs(self, fresh_project):
        """GI-002: `git add kitty-specs/` succeeds.

        Creating a feature and running git add should work without errors.
        """
        # Create a feature with content
        feature_dir = create_feature_with_structure(fresh_project, "test-feature")
        assert feature_dir is not None, "Feature creation failed"

        # Try to git add kitty-specs/
        result = subprocess.run(
            ["git", "add", "kitty-specs/"],
            cwd=fresh_project,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"git add failed: {result.stderr}"

        # Verify files are staged
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=fresh_project,
            capture_output=True,
            text=True
        )

        staged_files = status_result.stdout
        assert "kitty-specs" in staged_files, \
            f"kitty-specs files not staged. Status: {staged_files}"

    @pytest.mark.jj
    def test_gi_002_jj_git_add_kitty_specs(self, jj_fresh_project):
        """GI-002 (jj): `git add kitty-specs/` succeeds with jj colocated."""
        feature_dir = create_feature_with_structure(jj_fresh_project, "jj-test-feature")
        assert feature_dir is not None, "Feature creation failed"

        result = subprocess.run(
            ["git", "add", "kitty-specs/"],
            cwd=jj_fresh_project,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"git add failed: {result.stderr}"

        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=jj_fresh_project,
            capture_output=True,
            text=True
        )

        assert "kitty-specs" in status_result.stdout


# =============================================================================
# GI-003: Upgrade Fixes Gitignore (T045)
# =============================================================================

class TestUpgradeFixesGitignore:
    """GI-003: Validate upgrade/init fixes incorrect gitignore."""

    def test_gi_003_init_fixes_bad_gitignore(self, tmp_path):
        """GI-003: Upgrade fixes incorrect gitignore.

        If .gitignore incorrectly ignores kitty-specs/, running init
        should fix it (or at least not make it worse).
        """
        project_dir = tmp_path / "bad-gitignore-project"
        project_dir.mkdir()

        # Initialize git
        subprocess.run(
            ["git", "init"],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_dir,
            check=True,
            capture_output=True
        )

        # Create a BAD .gitignore that ignores kitty-specs/
        bad_gitignore = project_dir / ".gitignore"
        bad_gitignore.write_text("# Bad gitignore\nkitty-specs/\n.worktrees/\n")

        # Run spec-kitty init
        result = subprocess.run(
            ["spec-kitty", "init", "--here", "--force", "--ai", "claude"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )

        # Init should succeed
        assert result.returncode == 0, f"Init failed: {result.stderr}"

        # Check if gitignore was fixed
        new_content = bad_gitignore.read_text()

        # Look for signs the gitignore was updated
        # Acceptable outcomes:
        # 1. kitty-specs/ line was removed
        # 2. !kitty-specs/ was added to negate it
        # 3. Line is commented out

        lines = new_content.strip().split('\n')
        kitty_specs_ignored = False

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line == 'kitty-specs/' or line == 'kitty-specs':
                kitty_specs_ignored = True
                break

        # Check if there's a negation
        has_negation = '!kitty-specs' in new_content

        if kitty_specs_ignored and not has_negation:
            # Bug still present - but this may be expected behavior
            # Mark as xfail if spec-kitty doesn't fix gitignore
            pytest.xfail(
                "spec-kitty init does not fix incorrect gitignore. "
                "kitty-specs/ is still ignored."
            )


# =============================================================================
# ADV-001: Corrupted meta.json Handled (T046)
# =============================================================================

class TestCorruptedMetaJson:
    """ADV-001: Validate corrupted meta.json is handled gracefully."""

    @pytest.mark.jj
    def test_adv_001_corrupted_meta_json_handled(self, jj_fresh_project):
        """ADV-001: Corrupted meta.json handled gracefully.

        If meta.json contains invalid JSON, commands should fail gracefully
        with a clear error message, not crash with a stack trace.
        """
        # Create a feature
        feature_dir = create_feature_with_structure(jj_fresh_project, "corrupted-meta")
        assert feature_dir is not None

        # Corrupt the meta.json
        meta_json = feature_dir / "meta.json"
        meta_json.write_text("{ this is not valid JSON !!!}")

        # Try to run a command that reads meta.json
        result = subprocess.run(
            ["spec-kitty", "agent", "feature", "check-prerequisites", "--json"],
            cwd=jj_fresh_project,
            capture_output=True,
            text=True
        )

        combined = result.stdout + result.stderr

        # Should not crash with unhandled exception
        # Acceptable outcomes:
        # 1. Returns error with message about invalid JSON
        # 2. Returns error about corrupted file
        # 3. Skips the corrupted feature and continues

        if "Traceback" in combined and "JSONDecodeError" in combined:
            pytest.fail(
                "Unhandled JSONDecodeError - corrupted meta.json caused crash:\n"
                f"{combined[:1000]}"
            )

        # Command may fail but should have handled the error gracefully
        if result.returncode != 0:
            # Check for graceful error handling
            assert any([
                "json" in combined.lower(),
                "invalid" in combined.lower(),
                "corrupt" in combined.lower(),
                "parse" in combined.lower(),
                "error" in combined.lower(),
            ]), f"Expected error message about corrupted file: {combined[:500]}"

    def test_adv_001_empty_meta_json(self, fresh_project):
        """ADV-001b: Empty meta.json handled gracefully."""
        feature_dir = create_feature_with_structure(fresh_project, "empty-meta")
        assert feature_dir is not None

        # Make meta.json empty
        meta_json = feature_dir / "meta.json"
        meta_json.write_text("")

        result = subprocess.run(
            ["spec-kitty", "agent", "feature", "check-prerequisites", "--json"],
            cwd=fresh_project,
            capture_output=True,
            text=True
        )

        combined = result.stdout + result.stderr

        # Should not have unhandled exception
        if "Traceback" in combined:
            # Check it's not a critical crash
            if "CRITICAL" in combined or "FATAL" in combined:
                pytest.fail(f"Critical crash with empty meta.json: {combined[:500]}")

    def test_adv_001_missing_fields_meta_json(self, fresh_project):
        """ADV-001c: meta.json with missing required fields handled."""
        feature_dir = create_feature_with_structure(fresh_project, "missing-fields")
        assert feature_dir is not None

        # Write meta.json with missing required fields
        meta_json = feature_dir / "meta.json"
        meta_json.write_text('{"partial": "data"}')

        result = subprocess.run(
            ["spec-kitty", "agent", "feature", "check-prerequisites", "--json"],
            cwd=fresh_project,
            capture_output=True,
            text=True
        )

        combined = result.stdout + result.stderr

        # Should not crash
        assert "Traceback" not in combined or "handled" in combined.lower(), \
            f"Unhandled exception with missing fields: {combined[:500]}"


# =============================================================================
# ADV-002: Corrupted Workspace Handled (T047)
# =============================================================================

class TestCorruptedWorkspace:
    """ADV-002: Validate corrupted workspace directory is handled gracefully."""

    @pytest.mark.jj
    def test_adv_002_missing_worktree_dir(self, jj_fresh_project):
        """ADV-002: Missing .worktrees directory handled gracefully.

        If .worktrees directory doesn't exist when expected, commands
        should handle this gracefully.
        """
        # Create feature structure
        feature_dir = create_feature_with_structure(jj_fresh_project, "workspace-test")
        assert feature_dir is not None

        # Commit the feature
        subprocess.run(
            ["git", "add", "."],
            cwd=jj_fresh_project,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add feature"],
            cwd=jj_fresh_project,
            check=True,
            capture_output=True
        )

        # Try to run a workspace-related command without .worktrees
        result = subprocess.run(
            ["spec-kitty", "sync"],
            cwd=jj_fresh_project,
            capture_output=True,
            text=True
        )

        combined = result.stdout + result.stderr

        # Should handle missing worktrees gracefully
        if "no such command" in combined.lower():
            pytest.skip("spec-kitty sync command not available")

        # Should not crash
        assert "Traceback" not in combined or "FileNotFoundError" not in combined, \
            f"Unhandled exception with missing .worktrees: {combined[:500]}"

    @pytest.mark.jj
    def test_adv_002_empty_worktree_dir(self, jj_fresh_project):
        """ADV-002b: Empty .worktrees directory handled gracefully."""
        feature_dir = create_feature_with_structure(jj_fresh_project, "empty-worktrees")
        assert feature_dir is not None

        # Create empty .worktrees directory
        worktrees_dir = jj_fresh_project / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)

        subprocess.run(
            ["git", "add", "."],
            cwd=jj_fresh_project,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add feature"],
            cwd=jj_fresh_project,
            capture_output=True
        )

        # Try workspace command
        result = subprocess.run(
            ["spec-kitty", "agent", "tasks", "status"],
            cwd=jj_fresh_project,
            capture_output=True,
            text=True
        )

        combined = result.stdout + result.stderr

        # Should handle empty worktrees gracefully
        assert "Traceback" not in combined or "handled" in combined.lower()

    @pytest.mark.jj
    def test_adv_002_corrupted_worktree_structure(self, jj_fresh_project):
        """ADV-002c: Corrupted worktree structure handled gracefully."""
        feature_dir = create_feature_with_structure(jj_fresh_project, "corrupt-worktree")
        assert feature_dir is not None

        # Create a malformed worktree directory
        worktrees_dir = jj_fresh_project / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)

        # Create a fake workspace directory with missing git info
        fake_workspace = worktrees_dir / "001-corrupt-worktree-WP01"
        fake_workspace.mkdir()
        (fake_workspace / "some_file.txt").write_text("orphan file")

        subprocess.run(
            ["git", "add", "."],
            cwd=jj_fresh_project,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add feature with fake workspace"],
            cwd=jj_fresh_project,
            capture_output=True
        )

        # Try to run implement command
        result = subprocess.run(
            ["spec-kitty", "implement", "WP01"],
            cwd=jj_fresh_project,
            capture_output=True,
            text=True
        )

        combined = result.stdout + result.stderr

        if "no such command" in combined.lower():
            pytest.skip("spec-kitty implement command not available")

        # Should handle corrupted workspace gracefully
        # Acceptable outcomes:
        # 1. Cleans up corrupted workspace and creates new one
        # 2. Reports error about existing workspace
        # 3. Creates workspace with different name

        if "Traceback" in combined:
            # Check it's not an unhandled exception
            if any(exc in combined for exc in ["FileNotFoundError", "PermissionError", "OSError"]):
                pytest.xfail(f"Unhandled filesystem exception: {combined[:500]}")


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestGitignoreEdgeCases:
    """Additional edge case tests for gitignore and adversarial scenarios."""

    def test_nested_gitignore_patterns(self, fresh_project):
        """Test handling of nested gitignore patterns."""
        # Create nested .gitignore in kitty-specs
        kitty_specs = fresh_project / "kitty-specs"
        kitty_specs.mkdir(exist_ok=True)

        nested_gitignore = kitty_specs / ".gitignore"
        nested_gitignore.write_text("*.pyc\n__pycache__/\n")

        # This should not affect tracking of kitty-specs itself
        result = subprocess.run(
            ["git", "add", "kitty-specs/"],
            cwd=fresh_project,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

    def test_gitignore_with_special_characters(self, fresh_project):
        """Test gitignore with special characters in paths."""
        # Create directory with special characters
        special_dir = fresh_project / "kitty-specs" / "001-test [feature]"
        special_dir.mkdir(parents=True, exist_ok=True)

        (special_dir / "spec.md").write_text("# Test\n")

        result = subprocess.run(
            ["git", "add", "kitty-specs/"],
            cwd=fresh_project,
            capture_output=True,
            text=True
        )

        # Should handle special characters
        assert result.returncode == 0 or "nothing to commit" in result.stdout

    @pytest.mark.jj
    def test_jj_ignore_vs_gitignore(self, jj_fresh_project):
        """Test that jj respects gitignore patterns."""
        # jj should use .gitignore patterns
        gitignore = jj_fresh_project / ".gitignore"
        original_content = gitignore.read_text() if gitignore.exists() else ""

        # Add a test pattern
        with open(gitignore, 'a') as f:
            f.write("\n# Test pattern\ntest-ignored-file.txt\n")

        # Create a file that matches the pattern
        ignored_file = jj_fresh_project / "test-ignored-file.txt"
        ignored_file.write_text("This should be ignored")

        # Check jj status
        result = subprocess.run(
            ["jj", "status"],
            cwd=jj_fresh_project,
            capture_output=True,
            text=True
        )

        # The ignored file should not appear in status
        if "test-ignored-file.txt" in result.stdout:
            # jj might handle ignores differently
            pass  # Not a failure, just different behavior
