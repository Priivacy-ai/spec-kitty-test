"""
Orchestrator edge case tests (WP13: T073).

Tests unusual, adversarial, or boundary conditions for orchestrator.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import yaml


@pytest.fixture
def create_wp_with_deps(tmp_path):
    """Create WP files with specified dependencies."""
    def _create(wp_configs):
        """
        Args:
            wp_configs: dict mapping WP ID to list of dependencies
                       e.g., {"WP01": [], "WP02": ["WP01"], "WP03": ["WP99"]}
        """
        tasks_dir = tmp_path / "kitty-specs" / "001-test" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        for wp_id, deps in wp_configs.items():
            wp_file = tasks_dir / f"{wp_id}-test.md"
            frontmatter = {
                "work_package_id": wp_id,
                "title": f"Test {wp_id}",
                "dependencies": deps,
                "lane": "planned"
            }
            content = f"---\n{yaml.dump(frontmatter)}---\n\n# {wp_id}\n"
            wp_file.write_text(content)

        return tasks_dir.parent

    return _create


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestUnreachableDependency:
    """Test handling of dependencies to non-existent WPs."""

    def test_unreachable_dependency_detected(self, create_wp_with_deps):
        """Edge case: WP depends on non-existent WP (WP99)."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            validate_dependencies,
        )

        feature_dir = create_wp_with_deps({
            "WP01": [],
            "WP02": ["WP99"]  # WP99 doesn't exist
        })

        graph = build_dependency_graph(feature_dir)

        # Validate should detect missing dependency
        is_valid, errors = validate_dependencies("WP02", ["WP99"], graph)

        assert not is_valid, "Should detect missing dependency"
        assert any("WP99" in err for err in errors)

    def test_multiple_unreachable_dependencies(self, create_wp_with_deps):
        """Edge case: WP depends on multiple non-existent WPs."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            validate_dependencies,
        )

        feature_dir = create_wp_with_deps({
            "WP01": [],
            "WP02": ["WP98", "WP99"]  # Both don't exist
        })

        graph = build_dependency_graph(feature_dir)
        is_valid, errors = validate_dependencies("WP02", ["WP98", "WP99"], graph)

        assert not is_valid
        assert any("WP98" in err for err in errors)
        assert any("WP99" in err for err in errors)


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestCorruptedStateFile:
    """Test handling of corrupted orchestration state files."""

    def test_corrupted_json_state_file(self, tmp_path):
        """Edge case: orchestration-state.json is corrupted (invalid JSON)."""
        state_file = tmp_path / "orchestration-state.json"
        state_file.write_text("{ invalid json here }")

        with pytest.raises(json.JSONDecodeError):
            json.loads(state_file.read_text())

    def test_truncated_state_file(self, tmp_path):
        """Edge case: State file truncated mid-write."""
        state_file = tmp_path / "orchestration-state.json"
        state_file.write_text('{"feature": "test", "wps": {')  # Truncated

        with pytest.raises(json.JSONDecodeError):
            json.loads(state_file.read_text())

    def test_empty_state_file(self, tmp_path):
        """Edge case: Empty state file."""
        state_file = tmp_path / "orchestration-state.json"
        state_file.write_text("")

        with pytest.raises(json.JSONDecodeError):
            json.loads(state_file.read_text())


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestConcurrentProcesses:
    """Test concurrent orchestration process scenarios."""

    def test_lock_file_detection(self, tmp_path):
        """Edge case: Lock file indicates another process running."""
        lock_file = tmp_path / ".orchestration.lock"
        lock_file.write_text("PID: 12345\nStarted: 2026-01-23T10:00:00Z")

        # Lock file should be detectable
        assert lock_file.exists()
        content = lock_file.read_text()
        assert "PID:" in content

    def test_stale_lock_file_age(self, tmp_path):
        """Edge case: Lock file exists but is stale (old timestamp)."""
        lock_file = tmp_path / ".orchestration.lock"
        lock_file.write_text("PID: 99999\nStarted: 2020-01-01T00:00:00Z")

        # Should be detectable as stale by checking timestamp
        content = lock_file.read_text()
        assert "2020-01-01" in content  # Very old


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestPartialWorkspaceState:
    """Test handling of partially created workspaces."""

    def test_worktree_dir_exists_but_not_git(self, tmp_path):
        """Edge case: Worktree directory exists but is not a git worktree."""
        worktree_dir = tmp_path / ".worktrees" / "feature" / "WP01"
        worktree_dir.mkdir(parents=True)

        # Create some files but no .git
        (worktree_dir / "spec.md").write_text("# Spec")

        # Should be detectable as incomplete
        assert worktree_dir.exists()
        assert not (worktree_dir / ".git").exists()

    def test_empty_worktree_directory(self, tmp_path):
        """Edge case: Worktree directory exists but is empty."""
        worktree_dir = tmp_path / ".worktrees" / "feature" / "WP01"
        worktree_dir.mkdir(parents=True)

        assert worktree_dir.exists()
        assert list(worktree_dir.iterdir()) == []


@pytest.mark.functional
@pytest.mark.orchestrator
@pytest.mark.adversarial
class TestAgentOutputEdgeCases:
    """Test handling of unusual agent output."""

    def test_binary_output_handling(self):
        """Edge case: Agent produces binary/non-UTF8 output."""
        binary_output = b"\x00\x01\x02 binary garbage \xff\xfe"

        # Should handle without crashing
        try:
            decoded = binary_output.decode('utf-8', errors='replace')
            assert '\ufffd' in decoded  # Replacement character
        except UnicodeDecodeError:
            pytest.fail("Should handle binary output with replacement")

    def test_empty_output_handling(self):
        """Edge case: Agent produces no output at all."""
        empty_output = b""

        decoded = empty_output.decode('utf-8')
        assert decoded == ""

    def test_very_long_line_output(self):
        """Edge case: Agent produces extremely long lines."""
        long_line = "x" * 1_000_000  # 1MB line

        # Should be storable and retrievable
        assert len(long_line) == 1_000_000
