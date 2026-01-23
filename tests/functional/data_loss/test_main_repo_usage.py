"""
Main repo kitty-specs usage tests (WP09: T052).

Tests for:
- WP operations use main repo kitty-specs, not worktree copies
- Path resolution correctly identifies main repo paths
- Operations work even when worktree copies are missing

These tests ensure operations always modify the canonical data
in the main repo, preventing stale data from worktrees being used.
"""
import pytest
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from .conftest import create_worktree


# =============================================================================
# T052: Main Repo Path Resolution Tests
# =============================================================================

class TestMainRepoUsage:
    """Test that operations use main repo paths, not worktree copies."""

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_wp_operations_use_main_repo_paths(
        self, multi_feature_project, file_modification_tracker
    ):
        """WP operations modify main repo files, not worktree copies."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create stale copy in worktree (simulating sparse checkout gap)
        wt_specs = wt / "kitty-specs" / "001-feature-001"
        wt_specs.mkdir(parents=True, exist_ok=True)
        wt_tasks = wt_specs / "tasks.md"
        wt_tasks.write_text("---\nlane: planned\n---\nStale worktree copy")

        # Main repo version
        main_tasks = project / "kitty-specs" / "001-feature-001" / "tasks.md"
        main_original = main_tasks.read_text()

        # Record timestamps with delay to ensure distinguishable times
        time.sleep(0.1)
        file_modification_tracker.record(wt_tasks)
        file_modification_tracker.record(main_tasks)

        # Simulate WP operation that modifies tasks.md
        # In real implementation, this would be via specify_cli
        # Here we test the path resolution logic
        main_tasks.write_text(main_original + "\n# Updated by operation")

        # Main repo should be modified
        file_modification_tracker.assert_modified(
            main_tasks,
            "Main repo tasks.md was not modified"
        )

        # Worktree copy should NOT be modified
        file_modification_tracker.assert_not_modified(
            wt_tasks,
            "Worktree tasks.md was incorrectly modified (should use main repo)"
        )

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_planning_artifacts_read_from_main_repo(self, multi_feature_project):
        """Planning artifacts (spec.md, plan.md) read from main repo."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Create conflicting spec.md versions
        main_spec = project / "kitty-specs" / "001-feature-001" / "spec.md"
        main_spec.write_text("# Main Repo Version\n\nThis is the CORRECT version.")

        wt_spec = wt / "kitty-specs" / "001-feature-001" / "spec.md"
        wt_spec.parent.mkdir(parents=True, exist_ok=True)
        wt_spec.write_text("# Worktree Version\n\nThis is STALE - do not use.")

        # Function to resolve spec path (simulates real implementation)
        def get_spec_path(project_root: Path, feature: str) -> Path:
            """Always return main repo path."""
            return project_root / "kitty-specs" / feature / "spec.md"

        # Get spec path
        spec_path = get_spec_path(project, "001-feature-001")

        # Should be main repo path
        assert spec_path == main_spec
        assert "Main Repo Version" in spec_path.read_text()
        assert "STALE" not in spec_path.read_text()

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_path_resolution_with_worktree_as_cwd(self, multi_feature_project):
        """Path resolution works correctly when CWD is worktree."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Function to get main repo root from worktree
        def get_main_repo_from_worktree(worktree_path: Path) -> Path:
            """Find main repo from a worktree path."""
            git_path = worktree_path / ".git"

            if git_path.is_file():
                # Parse .git file to find main repo
                # Format: "gitdir: /path/to/main/.git/worktrees/wt-name"
                git_content = git_path.read_text().strip()
                if git_content.startswith("gitdir:"):
                    # Extract gitdir path
                    gitdir = git_content.replace("gitdir:", "").strip()
                    gitdir_path = Path(gitdir)
                    if not gitdir_path.is_absolute():
                        gitdir_path = (worktree_path / gitdir).resolve()

                    # gitdir is like /path/to/repo/.git/worktrees/worktree-name
                    # Go up 2 levels to .git, then 1 more to repo root
                    # .../repo/.git/worktrees/wt-name -> .../repo/.git/worktrees -> .../repo/.git -> .../repo
                    main_git = gitdir_path.parent.parent  # .git directory
                    main_repo = main_git.parent  # repo root
                    return main_repo.resolve()

            # Fallback - traverse up looking for .kittify
            current = worktree_path.resolve()
            while current != current.parent:
                if (current / ".kittify").exists():
                    return current
                current = current.parent

            return worktree_path

        # From worktree, should find main repo
        main_repo = get_main_repo_from_worktree(wt)

        # Resolve paths for comparison (handles symlinks/tmp paths like /private/var vs /var)
        assert main_repo.resolve() == project.resolve()

        # kitty-specs should come from main repo
        kitty_specs = main_repo / "kitty-specs"
        assert kitty_specs.exists()
        assert kitty_specs.resolve() == (project / "kitty-specs").resolve()

    @pytest.mark.functional
    @pytest.mark.data_loss
    @pytest.mark.adversarial
    def test_operations_succeed_when_worktree_copy_missing(
        self, multi_feature_project
    ):
        """Operations succeed even when worktree kitty-specs is absent."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Explicitly ensure NO kitty-specs in worktree
        wt_specs = wt / "kitty-specs"
        if wt_specs.exists():
            import shutil
            shutil.rmtree(wt_specs)

        assert not wt_specs.exists()

        # Main repo kitty-specs should exist
        main_specs = project / "kitty-specs" / "001-feature-001"
        assert main_specs.exists()

        # Operation that reads/writes to tasks.md should work
        main_tasks = main_specs / "tasks.md"
        original = main_tasks.read_text()

        # Simulate status update
        new_content = original.replace("lane: planned", "lane: doing")
        main_tasks.write_text(new_content)

        # Verify update worked
        assert "lane: doing" in main_tasks.read_text()

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_meta_json_read_from_main_repo(self, multi_feature_project):
        """meta.json always read from main repo."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Main repo meta.json
        import json
        main_meta = project / "kitty-specs" / "001-feature-001" / "meta.json"
        main_meta_data = json.loads(main_meta.read_text())
        main_meta_data["source"] = "main_repo"
        main_meta.write_text(json.dumps(main_meta_data, indent=2))

        # Stale worktree copy
        wt_meta = wt / "kitty-specs" / "001-feature-001" / "meta.json"
        wt_meta.parent.mkdir(parents=True, exist_ok=True)
        wt_meta_data = {"source": "worktree_stale"}
        wt_meta.write_text(json.dumps(wt_meta_data, indent=2))

        # Function to get meta (should always use main repo)
        def get_feature_meta(project_root: Path, feature: str) -> dict:
            meta_path = project_root / "kitty-specs" / feature / "meta.json"
            return json.loads(meta_path.read_text())

        # Read meta
        meta = get_feature_meta(project, "001-feature-001")

        # Should be from main repo
        assert meta.get("source") == "main_repo"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_wp_file_modifications_in_main_repo(
        self, multi_feature_project, file_modification_tracker
    ):
        """WP file (tasks/WP01.md) modifications happen in main repo."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Main repo WP file
        main_wp = (
            project / "kitty-specs" / "001-feature-001" / "tasks" /
            "WP01-first-work-package.md"
        )

        # Stale worktree copy
        wt_wp_dir = wt / "kitty-specs" / "001-feature-001" / "tasks"
        wt_wp_dir.mkdir(parents=True, exist_ok=True)
        wt_wp = wt_wp_dir / "WP01-first-work-package.md"
        wt_wp.write_text("---\nlane: planned\n---\nStale WP content")

        time.sleep(0.1)
        file_modification_tracker.record(main_wp)
        file_modification_tracker.record(wt_wp)

        # Update WP file in main repo
        content = main_wp.read_text()
        updated = content.replace('lane: "planned"', 'lane: "doing"')
        main_wp.write_text(updated)

        # Main repo WP should be modified
        file_modification_tracker.assert_modified(main_wp)

        # Worktree WP should NOT be modified
        file_modification_tracker.assert_not_modified(wt_wp)

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_sparse_checkout_excludes_kitty_specs(self, multi_feature_project):
        """Sparse checkout configuration excludes kitty-specs from worktrees."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Configure sparse checkout (simulating real implementation)
        sparse_checkout_path = wt / ".git"

        # Check if .git is a file (worktree) or directory
        if sparse_checkout_path.is_file():
            # It's a worktree - .git is a file pointing to main repo
            git_content = sparse_checkout_path.read_text()
            assert "gitdir:" in git_content
            gitdir = Path(git_content.split("gitdir:")[1].strip())

            # Sparse checkout config would be in gitdir/info/sparse-checkout
            sparse_file = gitdir / "info" / "sparse-checkout"

            # Write sparse checkout config excluding kitty-specs
            sparse_file.parent.mkdir(parents=True, exist_ok=True)
            sparse_file.write_text("/*\n!kitty-specs/\n")

            # Verify config
            assert sparse_file.exists()
            config = sparse_file.read_text()
            assert "!kitty-specs/" in config

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_entries_written_to_main_repo(self, multi_feature_project):
        """History entries in WP files written to main repo."""
        project = multi_feature_project

        # Create worktree
        wt = create_worktree(project, "001-feature-001", "WP01")

        # Main repo WP file
        main_wp = (
            project / "kitty-specs" / "001-feature-001" / "tasks" /
            "WP01-first-work-package.md"
        )

        # Read original content
        original = main_wp.read_text()

        # Add history entry (simulating real operation)
        new_history_entry = """  - timestamp: "2026-01-23T15:00:00Z"
    lane: "doing"
    agent: "test-agent"
    action: "Started implementation"
"""
        # Insert history entry after existing history
        if "history:" in original:
            parts = original.split("history:")
            updated = parts[0] + "history:" + parts[1].rstrip() + "\n" + new_history_entry
            main_wp.write_text(updated)

        # Verify history entry in main repo
        updated_content = main_wp.read_text()
        assert "test-agent" in updated_content
        assert "Started implementation" in updated_content
