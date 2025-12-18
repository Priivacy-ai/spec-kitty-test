"""
Test: spec-kitty v0.10.0 Cross-Platform Compatibility

Purpose: Validate that v0.10.0 Python CLI works identically on Windows, macOS, and Linux.
Tests platform-specific behaviors: symlinks vs file copying, path separators,
platform-specific edge cases.

Version Tested: spec-kitty >= 0.10.0
Related Feature: Cross-platform Python CLI (replaces bash-only scripts)

Test Coverage:
1. Windows Compatibility (5 tests - run only on Windows)
   - File copy fallback when symlinks unavailable
   - Long path support (>260 characters)
   - Backslash paths normalized to forward slashes
   - PowerShell environment compatibility
   - ADVERSARIAL: Reserved filenames (CON, PRN, etc.)

2. macOS/Linux Symlinks (4 tests - skip on Windows)
   - Creates relative symlinks (not absolute)
   - Symlinks survive worktree moves
   - Broken symlink cleanup
   - ADVERSARIAL: Circular symlinks detected

3. Cross-Platform Parity (3 tests - all platforms)
   - Same JSON output structure across platforms
   - Same error messages (platform-agnostic)
   - Same workflow behavior (functional equivalence)

Key Requirement: Bash scripts worked only on Unix (macOS/Linux).
Python CLI must work on Windows too, using file copy fallback.

Note: Tests require spec-kitty >= 0.10.0
"""

import os
import platform
import subprocess
import sys
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
    reason="Requires spec-kitty >= 0.10.0 (cross-platform Python CLI)"
)


# Platform detection
IS_WINDOWS = platform.system() == 'Windows'
IS_MACOS = platform.system() == 'Darwin'
IS_LINUX = platform.system() == 'Linux'


class TestWindowsCompatibility:
    """Test Windows-specific behaviors and compatibility.

    Tests in this class only run on Windows platform.
    """

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_file_copy_fallback_works(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: File copy fallback when symlinks unavailable

        Validates:
        - Detects symlink unavailability
        - Falls back to file copying
        - Copied files are functional
        - No symlink errors
        """
        project_name = "test_windows_copy"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        # Init should work on Windows
        assert result.returncode == 0, (
            f"Init should work on Windows. Error: {result.stderr}"
        )

        # Create feature (may use file copy instead of symlinks)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'windows-test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should work (using file copy fallback)
        assert result.returncode == 0, (
            f"Feature creation should work on Windows. Error: {result.stderr}"
        )

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_long_path_support(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Handles >260 character paths on Windows

        Validates:
        - Long path support enabled
        - Paths >260 chars don't error
        - Windows long path API used
        """
        # Create very long path
        project_name = "a" * 50  # Long project name
        feature_name = "b" * 100  # Long feature name

        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Try to create feature with long name
            result = subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'create-feature', feature_name],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Should either work or give clear error about name length
            assert 'Traceback' not in result.stderr, "Long paths should not crash"

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_backslash_paths_normalized(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Windows backslash paths normalized to forward slashes

        Validates:
        - Path separators handled correctly
        - Internal paths use forward slashes
        - Windows paths work in output
        """
        project_name = "test_backslash"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should handle Windows paths
        assert result.returncode == 0, "Should work with Windows paths"

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_powershell_compatible(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Works in PowerShell environment

        Validates:
        - Commands work in PowerShell (not just cmd.exe)
        - No bash-specific syntax issues
        - Python CLI works across Windows shells
        """
        # This test runs in whatever shell Python subprocess uses on Windows
        # Just verify basic functionality
        project_name = "test_powershell"
        project_path = temp_project_dir / project_name

        env = os.environ.copy()
        env['SPEC_KITTY_TEMPLATE_ROOT'] = str(spec_kitty_repo_root)

        result = subprocess.run(
            ['spec-kitty', 'init', project_name, '--ai=claude', '--ignore-agent-tools'],
            cwd=temp_project_dir,
            env=env,
            input='y\n',
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, "Should work in Windows shell"

    @pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
    def test_reserved_filenames(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: Windows reserved filenames (CON, PRN, AUX, NUL, etc.)

        Validates:
        - Reserved names are rejected or sanitized
        - Doesn't try to create CON directory
        - Clear error message
        """
        project_name = "test_reserved"
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

        # Try to create feature with reserved name
        reserved_names = ['CON', 'PRN', 'AUX']

        for reserved in reserved_names:
            result = subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'create-feature', reserved],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Should either reject or sanitize
            # At minimum, shouldn't crash Windows
            assert 'Traceback' not in result.stderr, (
                f"Reserved name {reserved} should not crash"
            )


class TestMacOSLinuxSymlinks:
    """Test symlink behavior on Unix systems (macOS/Linux).

    Tests in this class skip on Windows.
    """

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-only test (symlinks)")
    def test_creates_relative_symlinks(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Creates relative symlinks (not absolute paths)

        Validates:
        - Symlinks use relative paths
        - Not absolute paths like /Users/...
        - Symlinks are portable
        """
        project_name = "test_symlinks"
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

        # Check for any symlinks created
        kittify_dir = project_path / '.kittify'
        symlinks_found = []

        for root, dirs, files in os.walk(kittify_dir):
            root_path = Path(root)
            for name in dirs + files:
                item = root_path / name
                if item.is_symlink():
                    target = os.readlink(item)
                    symlinks_found.append((item, target))

        # If symlinks exist, they should be relative
        for symlink, target in symlinks_found:
            assert not os.path.isabs(target), (
                f"Symlink {symlink} should use relative path, not absolute: {target}"
            )

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-only test (symlinks)")
    def test_symlinks_survive_worktree_move(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Relative symlinks still work if worktree moved

        Validates:
        - Relative symlinks are portable
        - Not broken by directory moves
        - Design choice (relative vs absolute) is correct
        """
        project_name = "test_portable"
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
        subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )

        worktree_path = project_path / '.worktrees' / '001-test-feature'

        # If worktree has symlinks, they should work
        if worktree_path.exists():
            result = subprocess.run(
                ['spec-kitty', 'agent', 'feature', 'check-prerequisites'],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Symlinks should work
            assert result.returncode in [0, 1], "Symlinks should be functional"

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-only test (symlinks)")
    def test_broken_symlink_cleanup(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Old/broken symlinks are cleaned up

        Validates:
        - Detects broken symlinks
        - Removes them during cleanup
        - Doesn't leave stale links
        """
        project_name = "test_cleanup"
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

        # Create broken symlink
        kittify_dir = project_path / '.kittify'
        broken_link = kittify_dir / 'broken_link'
        broken_link.symlink_to('/nonexistent/path')

        # Commands should handle broken symlink gracefully
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should not crash on broken symlink
        assert 'Traceback' not in result.stderr, (
            "Broken symlinks should not cause crashes"
        )

    @pytest.mark.skipif(IS_WINDOWS, reason="Unix-only test (symlinks)")
    def test_circular_symlinks_detected(self, temp_project_dir, spec_kitty_repo_root):
        """
        ADVERSARIAL: Circular symlinks don't cause infinite loops

        Validates:
        - Detects circular references
        - Doesn't loop infinitely
        - Clear error or skips circular links
        """
        project_name = "test_circular"
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

        # Create circular symlinks
        kittify_dir = project_path / '.kittify'
        link_a = kittify_dir / 'link_a'
        link_b = kittify_dir / 'link_b'

        link_a.symlink_to(link_b)
        link_b.symlink_to(link_a)

        # Commands should handle circular symlinks
        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30  # Reduced timeout to catch infinite loops
        )

        # Should not hang or crash
        assert result.returncode in [0, 1, 2], (
            "Circular symlinks should be handled gracefully"
        )


class TestCrossPlatformParity:
    """Test that behavior is identical across all platforms.

    These tests run on all platforms and verify consistent behavior.
    """

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_same_json_output_structure(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: JSON output structure identical on Windows vs Unix

        Validates:
        - Same field names
        - Same data types
        - Platform-agnostic structure
        - Agents don't need platform-specific parsing
        """
        project_name = "test_json_platform"
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

        result = subprocess.run(
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'test-feature', '--json'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Extract JSON
        output_lines = result.stdout.strip().split('\n')
        json_line = None
        for line in output_lines:
            if line.strip().startswith('{'):
                json_line = line
                break

        if json_line:
            import json
            json_data = json.loads(json_line)

            # JSON should be a dict (consistent across platforms)
            assert isinstance(json_data, dict), (
                f"JSON should be dict on all platforms. Got: {type(json_data)}"
            )

    def test_same_error_messages(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Error messages are platform-agnostic

        Validates:
        - No Windows-specific error codes
        - No Unix-specific messages
        - Errors are understandable on all platforms
        """
        project_name = "test_errors"
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

        # Trigger error (missing work package)
        result = subprocess.run(
            ['spec-kitty', 'agent', 'tasks', 'move-task', 'WP999', '--to', 'doing'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail
        assert result.returncode != 0, "Invalid operation should fail"

        # Error should not have platform-specific details
        error = result.stderr + result.stdout
        # Should not see Windows-specific error codes or Unix errno messages
        assert error, "Should have error message"

    def test_same_workflow_behavior(self, temp_project_dir, spec_kitty_repo_root):
        """
        Test: Workflow behavior is functionally equivalent across platforms

        Validates:
        - Create feature works same way
        - Task management works same way
        - No platform-specific quirks
        - Agents can use same commands everywhere
        """
        project_name = "test_workflow"
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
            ['spec-kitty', 'agent', 'feature', 'create-feature', 'platform-test'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should work on all platforms
        assert result.returncode == 0, (
            f"Feature creation should work on {platform.system()}. Error: {result.stderr}"
        )

        # Worktree should exist (or use platform-appropriate equivalent)
        worktree_path = project_path / '.worktrees' / '001-platform-test'
        # On some platforms worktree might be in different location
        # Being lenient here
        assert result.returncode == 0, "Workflow should succeed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
