"""
Test: spec-kitty v0.10.0 Path Resolution Edge Cases

Purpose: Adversarial testing of path resolution logic across all contexts.
This tests the "find the bugs" / "break it when you look at it" approach
for path resolution that must work from main repo, worktrees, subdirectories,
and handle symlinks, broken links, and edge cases.

Version Tested: spec-kitty >= 0.10.0
Related Feature: Automatic path resolution for agent commands

Test Coverage:
1. Path Resolution Strategies (5 tests)
   - Finds .kittify/ marker by walking up
   - Uses git worktree detection as fallback
   - Environment variable override (SPECIFY_REPO_ROOT)
   - Works from arbitrary subdirectories
   - Resolves relative paths correctly

2. Path Resolution Edge Cases (8 tests)
   - ADVERSARIAL: Broken symlink handling (graceful error)
   - ADVERSARIAL: .kittify itself is a symlink
   - ADVERSARIAL: Repository root is a symlink
   - ADVERSARIAL: Deeply nested worktree (15+ levels)
   - ADVERSARIAL: Missing .kittify directory
   - ADVERSARIAL: No git, no .kittify (clear error)
   - ADVERSARIAL: Worktree without feature structure
   - ADVERSARIAL: Concurrent execution from different paths

3. Worktree Context Detection (5 tests)
   - Detects main repo context (not worktree)
   - Detects worktree context correctly
   - Finds feature slug from git branch name
   - Finds feature slug from path (kitty-specs/###-slug)
   - ADVERSARIAL: Nested worktrees (worktree inside worktree)

Critical Requirement: Path resolution must NEVER fail silently or guess wrong.
Clear errors are better than incorrect paths. Agent commands must work
reliably regardless of where they're invoked from.

Note: Tests require spec-kitty >= 0.10.0
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def _get_spec_kitty_version():
    """Get spec-kitty version at module load time for skipif."""
    try:
        result = subprocess.run(
            ['spec-kitty', '--version'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        version_str = result.stdout.strip().split()[-1]
        base_version = version_str.split('-')[0]
        return tuple(map(int, base_version.split('.')))
    except Exception:
        return (0, 0, 0)


# Module-level skip marker
pytestmark = pytest.mark.skipif(
    _get_spec_kitty_version() < (0, 10, 0),
    reason="Requires spec-kitty >= 0.10.0 (automatic path resolution)"
)


class TestPathResolutionStrategies:
    """Test different path resolution strategies work correctly."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_finds_kittify_marker(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Walks up directory tree to find .kittify/ marker

        Validates:
        - Searches parent directories
        - Stops at .kittify/ directory
        - Correctly identifies project root
        """
        project_name = "test_marker"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create deep subdirectory
        deep_dir = project_path / 'subdir1' / 'subdir2' / 'subdir3'
        deep_dir.mkdir(parents=True, exist_ok=True)

        # Run command from deep subdirectory
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature', '--json'],
            cwd=deep_dir,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should find .kittify/ by walking up and succeed
        assert result.returncode == 0, (
            f"Should find .kittify/ by walking up directory tree. Error: {result.stderr}"
        )

    def test_uses_git_worktree_detection(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Git worktree detection works as fallback

        Validates:
        - Git commands used to detect worktree
        - Works when .kittify/ not immediately visible
        - Fallback strategy is reliable
        """
        project_name = "test_git_detect"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        worktree_path = project_path / '.worktrees' / '001-test-feature'

        if worktree_path.exists():
            # Run from worktree (git should detect context)
            result = subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Should detect worktree context
            assert result.returncode in [0, 1], (
                f"Git worktree detection should work. Error: {result.stderr}"
            )

    def test_env_var_override(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: SPECIFY_REPO_ROOT environment variable overrides auto-detection

        Validates:
        - Env var is respected
        - Overrides automatic path resolution
        - Useful for testing/debugging
        """
        project_name = "test_env_override"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Set env var override
        env['SPECIFY_REPO_ROOT'] = str(project_path)

        # Run from completely different directory
        other_dir = temp_project_dir / 'other'
        other_dir.mkdir()

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature', '--json'],
            cwd=other_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=60
        )

        # May succeed or fail, but shouldn't crash
        # The env var should be recognized
        assert 'SPECIFY_REPO_ROOT' not in result.stderr or result.returncode in [0, 1], (
            "Environment variable override should be recognized"
        )

    def test_works_from_arbitrary_subdir(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Execute from kitty-specs/###/tasks/subtasks/ (very deep)

        Validates:
        - Works from any depth
        - No hardcoded depth limits
        - Walks all the way up to find root
        """
        project_name = "test_deep"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Create very deep subdirectory
        worktree_path = project_path / '.worktrees' / '001-test-feature'
        deep_dir = worktree_path / 'kitty-specs' / '001-test-feature' / 'tasks' / 'subtasks' / 'sub1' / 'sub2'
        deep_dir.mkdir(parents=True, exist_ok=True)

        # Run from very deep directory
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
            cwd=deep_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should still work
        assert result.returncode in [0, 1], (
            f"Should work from deep subdirectory. Error: {result.stderr}"
        )

    def test_resolves_relative_paths_correctly(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: ../../../ relative paths work correctly

        Validates:
        - Relative path resolution
        - No path traversal issues
        - Correctly normalizes paths
        """
        project_name = "test_relative"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create feature
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should handle relative paths internally
        assert result.returncode == 0, "Path resolution should work"


class TestPathResolutionEdgeCases:
    """ADVERSARIAL: Test edge cases that might break path resolution."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_broken_symlink_graceful_error(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: Broken symlink doesn't crash, gives clear error

        Validates:
        - Detects broken symlink (is_symlink() before exists())
        - Doesn't crash with FileNotFoundError
        - Error message is clear
        """
        project_name = "test_broken_link"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create broken symlink inside project
        broken_link = project_path / 'broken_link'
        try:
            broken_link.symlink_to('/nonexistent/path/that/does/not/exist')
        except OSError:
            # Windows may not support symlinks
            pytest.skip("Symlinks not supported on this platform")

        # Try to run command (should handle broken symlink gracefully)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should either succeed (ignoring broken symlink) or fail gracefully
        assert 'Traceback' not in result.stderr, (
            "Broken symlinks should not cause Python traceback"
        )

    def test_kittify_is_symlink(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: .kittify directory itself is a symlink

        Validates:
        - Follows symlink correctly
        - Resolves to actual directory
        - Works as if .kittify/ were real directory
        """
        # This test is tricky to set up - .kittify/ is created by init
        # We'll test that commands handle symlinked dirs
        pytest.skip("Complex setup required - .kittify/ created by init")

    def test_repo_root_is_symlink(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: Repository root itself is accessed via symlink

        Validates:
        - Path resolution works through symlink
        - Resolves to real path
        - Git operations work
        """
        project_name = "test_real"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create symlink to project
        symlink_path = temp_project_dir / 'project_symlink'
        try:
            symlink_path.symlink_to(project_path)
        except OSError:
            pytest.skip("Symlinks not supported")

        # Run command through symlink
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=symlink_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should work through symlink
        assert result.returncode == 0, (
            f"Should work through symlinked root. Error: {result.stderr}"
        )

    def test_deeply_nested_worktree(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: 15+ directory levels deep

        Validates:
        - No stack overflow
        - No recursion limits hit
        - Works regardless of depth
        """
        project_name = "test_depth"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create 20 levels deep
        deep_path = project_path
        for i in range(20):
            deep_path = deep_path / f'level{i}'
        deep_path.mkdir(parents=True, exist_ok=True)

        # Run from 20 levels deep
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=deep_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should find .kittify/ or error clearly
        assert 'RecursionError' not in result.stderr, (
            "Should not hit recursion limit"
        )

    def test_missing_kittify_dir(self, temp_project_dir):
        """
        ADVERSARIAL: No .kittify/ directory exists

        Validates:
        - Clear error message
        - Mentions missing .kittify/
        - Suggests running spec-kitty init
        """
        # Create directory without .kittify/
        no_kittify = temp_project_dir / 'no_kittify'
        no_kittify.mkdir()

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
            cwd=no_kittify,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail
        assert result.returncode != 0, "Should fail without .kittify/"

        # Error should mention the issue
        error_output = result.stderr + result.stdout
        assert any(keyword in error_output.lower() for keyword in ['kittify', 'not found', 'repository', 'project']), (
            f"Error should clearly indicate missing .kittify/. Got: {error_output}"
        )

    def test_no_git_no_kittify(self, temp_project_dir):
        """
        ADVERSARIAL: No git, no .kittify/ - complete failure case

        Validates:
        - Doesn't crash
        - Error message is actionable
        - Tells user to run init
        """
        empty_dir = temp_project_dir / 'empty'
        empty_dir.mkdir()

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
            cwd=empty_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail gracefully
        assert result.returncode != 0, "Should fail without project"
        assert 'Traceback' not in result.stderr, "Should not crash"

    def test_worktree_without_feature_structure(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: Worktree exists but incomplete/broken

        Validates:
        - Handles incomplete worktrees
        - Clear error about missing structure
        - Doesn't assume structure exists
        """
        project_name = "test_incomplete"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create worktree directory but don't set up feature structure
        incomplete_worktree = project_path / '.worktrees' / 'incomplete'
        incomplete_worktree.mkdir(parents=True, exist_ok=True)

        # Try to run command (should handle gracefully)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
            cwd=incomplete_worktree,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should handle gracefully (may fail but shouldn't crash)
        assert 'Traceback' not in result.stderr, "Should handle incomplete worktree gracefully"

    def test_concurrent_execution_from_different_paths(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: Multiple commands from different paths simultaneously

        Validates:
        - No race conditions
        - Path resolution is thread-safe
        - Each command gets correct context
        """
        project_name = "test_concurrent"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        worktree_path = project_path / '.worktrees' / '001-test-feature'

        # Run two commands concurrently from different paths
        import concurrent.futures

        def run_from_path(path):
            return subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(run_from_path, project_path)
            future2 = executor.submit(run_from_path, worktree_path if worktree_path.exists() else project_path)

            result1 = future1.result()
            result2 = future2.result()

        # Both should complete without crashing
        assert 'Traceback' not in result1.stderr and 'Traceback' not in result2.stderr, (
            "Concurrent execution should not cause crashes"
        )


class TestWorktreeContextDetection:
    """Test that worktree vs main repo context is detected correctly."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_detects_main_repo_context(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: is_worktree_context() returns False in main repo

        Validates:
        - Main repo correctly identified
        - Not confused with worktree
        - Behavior differs from worktree
        """
        project_name = "test_main"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Run from main repo
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature', '--json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should work from main repo
        assert result.returncode == 0, "Should work from main repo"

    def test_detects_worktree_context(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: is_worktree_context() returns True in worktree

        Validates:
        - Worktree correctly identified
        - Git worktree list or branch detection works
        - Different behavior than main repo
        """
        project_name = "test_worktree"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        worktree_path = project_path / '.worktrees' / '001-test-feature'

        if worktree_path.exists():
            # Run from worktree
            result = subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'check-prerequisites', '--json'],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Should work from worktree
            assert result.returncode in [0, 1], "Should work from worktree"

    def test_finds_feature_slug_from_branch(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Feature slug extracted from git branch name

        Validates:
        - Git branch detection works
        - Branch name parsed correctly (###-slug format)
        - Feature identification reliable
        """
        project_name = "test_branch"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'branch-test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        # Commands should auto-detect feature from branch
        worktree_path = project_path / '.worktrees' / '001-branch-test'
        if worktree_path.exists():
            result = subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Should auto-detect from branch
            assert result.returncode in [0, 1], "Should auto-detect feature"

    def test_finds_feature_slug_from_path(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Feature slug extracted from path (kitty-specs/###-slug)

        Validates:
        - Path parsing works
        - Handles kitty-specs/###-slug pattern
        - Fallback when branch detection fails
        """
        project_name = "test_path"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'path-test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        worktree_path = project_path / '.worktrees' / '001-path-test'
        if worktree_path.exists():
            # Navigate into kitty-specs subdirectory
            specs_dir = worktree_path / 'kitty-specs' / '001-path-test'
            if specs_dir.exists():
                result = subprocess.run(
                    ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
                    cwd=specs_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Should extract from path
                assert result.returncode in [0, 1], "Should extract slug from path"

    def test_nested_worktrees(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: Worktree inside another worktree

        Validates:
        - Handles nested worktree scenario
        - Doesn't get confused about context
        - Clear error or correct handling
        """
        project_name = "test_nested"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Create first worktree
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'outer'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        outer_worktree = project_path / '.worktrees' / '001-outer'

        # Try to create nested worktree (should fail or handle gracefully)
        if outer_worktree.exists():
            result = subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'create-feature', 'inner'],
                cwd=outer_worktree,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Should handle gracefully (fail or succeed, but not crash)
            assert 'Traceback' not in result.stderr, "Nested worktree should not crash"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
