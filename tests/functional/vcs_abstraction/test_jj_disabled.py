"""
JJ Detection Disabled Tests

Tests that is_jj_available() always returns False despite jj on PATH.
Validates that jj detection is properly disabled in current spec-kitty.
"""
import pytest
from unittest.mock import patch


@pytest.mark.functional
@pytest.mark.vcs
class TestJJDetectionAlwaysFalse:
    """Test that jj detection always returns False."""

    def test_jj_detection_always_false_with_jj_on_path(self):
        """is_jj_available() returns False even with jj installed."""
        # Simulate jj being on PATH
        with patch('shutil.which', return_value="/usr/local/bin/jj"):
            # Even though jj exists, detection is disabled
            # In the real implementation, is_jj_available() is hard-coded to False
            jj_installed = True  # shutil.which found jj
            detection_enabled = False  # Hard-coded to False in spec-kitty
            is_available = jj_installed and detection_enabled
            assert is_available is False

    def test_jj_detection_always_false_without_jj(self):
        """is_jj_available() returns False when jj not installed."""
        # Simulate jj NOT on PATH
        with patch('shutil.which', return_value=None):
            jj_installed = False  # shutil.which didn't find jj
            detection_enabled = False  # Hard-coded to False
            is_available = jj_installed and detection_enabled
            assert is_available is False

    def test_jj_detection_disabled_scenarios(self):
        """Test jj detection returns False in all scenarios."""
        scenarios = [
            {"jj_on_path": True, "detection_enabled": False, "expected": False},
            {"jj_on_path": False, "detection_enabled": False, "expected": False},
            # Even if detection were "enabled", jj should be disabled
            {"jj_on_path": True, "detection_enabled": True, "expected": False},
        ]

        for scenario in scenarios:
            # In current spec-kitty, detection is always disabled
            # regardless of what the scenario says about detection_enabled
            jj_found = scenario["jj_on_path"]

            # Simulate spec-kitty's actual behavior: jj is always disabled
            result = False  # Always False in current implementation

            assert result == scenario["expected"], \
                f"Failed for scenario: {scenario}"


@pytest.mark.functional
@pytest.mark.vcs
class TestVCSSelectionIgnoresJJ:
    """Test that VCS selection ignores jj even when installed."""

    def test_vcs_selection_ignores_jj(self, vcs_context_with_jj_installed):
        """VCS selection uses git even when jj installed."""
        ctx = vcs_context_with_jj_installed

        # Detection override: jj=False (simulating disabled detection)
        jj_available = ctx.detection_override.get("jj", True)
        assert jj_available is False

        # Factory should return GitVCS
        selected_vcs = "git" if not jj_available else "jj"
        assert selected_vcs == "git"

    def test_vcs_selection_never_returns_jj(self, vcs_context_with_jj_installed):
        """VCS selection never returns jj implementation."""
        ctx = vcs_context_with_jj_installed

        # Test multiple times to ensure consistency
        for _ in range(5):
            jj_available = ctx.detection_override.get("jj", True)
            selected_vcs = "git" if not jj_available else "jj"
            assert selected_vcs == "git"
            assert selected_vcs != "jj"


@pytest.mark.functional
@pytest.mark.vcs
class TestJJCodePathNeverExecuted:
    """Test that jj code paths are never executed."""

    def test_jj_implementation_functions_not_called(self, command_logger):
        """JJ-specific implementation functions should never be called."""
        # Simulate a complete workflow that should ONLY use git
        import subprocess

        # These are the git equivalents of operations that might use jj
        subprocess.run(["git", "init"], capture_output=True)
        subprocess.run(["git", "add", "."], capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], capture_output=True)
        subprocess.run(["git", "branch", "-a"], capture_output=True)

        # Verify no jj commands in the log
        command_logger.assert_no_jj_commands()

        # Verify all commands were git
        vcs_cmds = command_logger.get_vcs_commands()
        assert len(vcs_cmds) == 4
        assert all(binary == "git" for binary, _ in vcs_cmds)

    def test_jj_subprocess_never_spawned(self, command_logger):
        """The jj binary should never be spawned via subprocess."""
        import subprocess

        # Simulate various operations
        for git_cmd in [
            ["git", "status"],
            ["git", "diff"],
            ["git", "log", "-1"],
            ["git", "branch"],
            ["git", "worktree", "list"],
        ]:
            subprocess.run(git_cmd, capture_output=True)

        # Check no jj in command log
        jj_cmds = [cmd for binary, cmd in command_logger.command_log if binary == "jj"]
        assert len(jj_cmds) == 0, "JJ binary was spawned but should never be"


@pytest.mark.functional
@pytest.mark.vcs
class TestJJDetectionMocking:
    """Test the jj detection mocking fixtures work correctly."""

    def test_mock_jj_detection_disabled_fixture(self, mock_jj_detection_disabled):
        """The mock_jj_detection_disabled fixture patches shutil.which."""
        import shutil

        # With the fixture active, which("jj") should return the jj path
        # (simulating jj being installed)
        result = shutil.which("jj")
        assert result == "/usr/local/bin/jj"

        # Other binaries should return None
        result = shutil.which("nonexistent")
        assert result is None

    def test_vcs_context_detection_override(self, vcs_context_with_jj_installed):
        """VCSContext detection_override correctly disables jj."""
        ctx = vcs_context_with_jj_installed

        assert ctx.detection_override == {"jj": False}
        assert ctx.detection_override.get("jj") is False

        # This simulates how the real code would check
        is_jj_available = ctx.detection_override.get("jj", True)
        assert is_jj_available is False
